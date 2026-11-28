"""Bounded, all-or-nothing Papyrus project builds.

Flat, unnamespaced source libraries only. Dependency discovery is advisory;
the native compiler is authoritative. No incremental-cache claims.
"""
from pathlib import Path
import json
import re
import shutil
import tempfile
from .integrations import executable, file, directory, fresh
from .papyrus_build import family, digest, build, inspect_pex
from .script_symbols import masked

NAME = r"[A-Za-z_][A-Za-z0-9_]*"
MAX_FILES = 2000
MAX_BYTES = 32 * 1024 * 1024

def inventory(source_root, imports):
    roots = list(dict.fromkeys(directory(p) for p in [source_root, *imports]))
    entries = {}
    size = 0
    for i, root in enumerate(roots):
        for p in sorted(root.iterdir(), key=lambda x: x.name.casefold()):
            if p.suffix.casefold() != ".psc":
                continue
            if p.is_symlink() or not p.is_file():
                raise ValueError("unsafe source entry: "+str(p))
            if not re.fullmatch(NAME, p.stem):
                raise ValueError("only flat unnamespaced scripts supported: "+p.name)
            key = p.stem.casefold()
            if key in entries:
                raise ValueError("ambiguous script across source libraries: "+p.name)
            size += p.stat().st_size
            if len(entries) >= MAX_FILES or size > MAX_BYTES or p.stat().st_size > 512*1024:
                raise ValueError("source inventory size limit exceeded")
            data = p.read_bytes()
            import hashlib
            clean = masked(data.decode("utf-8-sig"), "papyrus")
            declaration = re.findall(r"(?im)^\s*Scriptname\s+("+NAME+r")(?:\s+extends\s+("+NAME+r"))?",clean)
            if len(declaration)!=1 or declaration[0][0].casefold()!=key:
                raise ValueError("Scriptname mismatch: "+p.name)
            parent = declaration[0][1].casefold()
            explicit = set(v.casefold() for v in re.findall(r"(?im)^\s*import\s+("+NAME+r")\b",clean))
            if parent: explicit.add(parent)
            entries[key] = {"path":str(p),"root":i,"name":p.name,
                            "sha256":hashlib.sha256(data).hexdigest(),
                            "extends":parent,"dependencies":sorted(explicit)}
    if not any(e["root"]==0 for e in entries.values()):
        raise ValueError("no project scripts in source directory")
    return roots, entries

def ordering(entries):
    # Inheritance cycles are invalid. Import cycles are reported, not treated
    # as proof of invalid source: compiler resolution may permit them.
    for key in entries:
        seen=set()
        node=key
        while node in entries:
            if node in seen: raise ValueError("inheritance cycle involving "+node)
            seen.add(node)
            node=entries[node]["extends"]
    pending={k for k,v in entries.items() if v["root"]==0}
    order=[]
    cycles=[]
    while pending:
        ready=sorted(k for k in pending if not (set(entries[k]["dependencies"]) & pending))
        if not ready:
            # Deterministic fallback for import cycles / dependent nodes.
            cycles=sorted(pending)
            order.extend(cycles)
            break
        order.extend(ready)
        pending.difference_update(ready)
    return order,cycles

def plan(game,backend,exe,source_root,flags,imports,output):
    family(game)
    if backend not in {"ck","caprica"}: raise ValueError("unsupported compiler")
    binary=executable(exe)
    flag=file(flags,{".flg"})
    out=fresh(output)
    roots,entries=inventory(source_root,imports)
    if any(out.is_relative_to(p) for p in roots+[flag.parent]):
        raise ValueError("output must be outside source/import/flags directories")
    order,cycles=ordering(entries)
    return {"game":game,"backend":backend,"compiler":binary,"compiler_sha256":digest(binary),
            "flags":str(flag),"flags_sha256":digest(flag),"output":str(out),
            "roots":list(map(str,roots)),"sources":entries,"order":order,
            "unresolved":{k:[d for d in e["dependencies"] if d not in entries]
                          for k,e in entries.items() if any(d not in entries for d in e["dependencies"])},
            "import_cycle_or_blocked":cycles,
            "scope":"flat PSC inventory; explicit extends/import edges only; compiler authoritative"}

def batch(game,backend,exe,source_root,flags,imports,output,*,execute=False,timeout=120):
    if type(timeout) is not int or not 1<=timeout<=900:
        raise ValueError("invalid per-script timeout")
    report=plan(game,backend,exe,source_root,flags,imports,output)
    if not execute:return report
    out=Path(report["output"])
    results=[]
    with tempfile.TemporaryDirectory(prefix=".chimster-batch-",dir=out.parent) as temp:
        root=Path(temp)
        libraries=[root/("source-"+str(i)) for i in range(len(report["roots"]))]
        for p in libraries:p.mkdir()
        for e in report["sources"].values():
            p=libraries[e["root"]]/e["name"]
            shutil.copyfile(e["path"],p)
            if digest(p)!=e["sha256"]:
                return {**report,"status":"inputs-changed","results":[]}
        flagdir=root/"flags"
        flagdir.mkdir()
        flag=flagdir/Path(report["flags"]).name
        shutil.copyfile(report["flags"],flag)
        if digest(flag)!=report["flags_sha256"] or digest(report["compiler"])!=report["compiler_sha256"]:
            return {**report,"status":"inputs-changed","results":[]}
        builds=root/"builds"
        builds.mkdir()
        staged=[]
        for key in report["order"]:
            e=report["sources"][key]
            dest=builds/key
            try:
                result=build(game,backend,report["compiler"],libraries[0]/e["name"],
                             flag,libraries[1:],dest,execute=True,timeout=timeout)
            except (OSError,ValueError,RuntimeError) as exc:
                result={"status":"error","message":str(exc)}
            results.append({"script":e["name"],"result":result})
            if result.get("status")!="header-checked":
                return {**report,"status":"batch-failed","results":results}
            pex=[p for p in dest.iterdir() if p.suffix.casefold()==".pex"]
            if len(pex)!=1 or pex[0].is_symlink() or digest(pex[0])!=result["artifact"]["sha256"]:
                return {**report,"status":"artifact-changed","results":results}
            staged.append((pex[0],result["artifact"]["sha256"]))
        # Recheck complete inventory, including additions/removals/imports.
        try:
            _,current=inventory(source_root,imports)
            intact=(current==report["sources"] and digest(flags)==report["flags_sha256"]
                    and digest(exe)==report["compiler_sha256"]
                    and all(digest(libraries[e["root"]]/e["name"])==e["sha256"]
                            for e in report["sources"].values()))
        except (OSError,ValueError):
            intact=False
        if not intact:return {**report,"status":"inputs-changed","results":results}
        final={**report,"status":"header-checked","results":results,
               "scope":"all scripts externally compiled; PEX headers checked, runtime unverified"}
        out.mkdir()
        created=[]
        try:
            for p,expected in staged:
                dest=out/p.name
                with dest.open("xb") as stream:
                    created.append(dest)
                    stream.write(p.read_bytes())
                if inspect_pex(dest,game)["sha256"]!=expected:
                    raise ValueError("published artifact hash mismatch")
            manifest=out/"batch.json"
            with manifest.open("x",encoding="utf-8") as stream:
                created.append(manifest)
                json.dump(final,stream,indent=2)
        except Exception:
            for p in reversed(created):p.unlink(missing_ok=True)
            out.rmdir()
            raise
        return final
