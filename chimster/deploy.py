"""Materialize a disposable profile Data directory with loose-file precedence.
Not a virtual filesystem; never modifies or links to source files."""
from pathlib import Path
import shutil,json,hashlib,os
from .validation import normalize

def stage_overlay(sources,output):
    roots=[Path(p).resolve(strict=True) for p in sources];out=Path(output).resolve()
    if not roots or any(not r.is_dir() or out.is_relative_to(r) or r.is_relative_to(out) for r in roots):raise ValueError("overlapping or invalid directories")
    if out.exists():raise FileExistsError(out)
    winners={};providers={}
    for root in roots:
        seen=set()
        for p in sorted(root.rglob("*")):
            if p.is_symlink():raise ValueError("symlink in source")
            if not p.is_file():continue
            rel=p.relative_to(root).as_posix();key=normalize(rel)
            if key in seen:raise ValueError("case collision")
            seen.add(key);winners[key]=p;providers.setdefault(key,[]).append(str(p))
    # Refuse file/directory collisions rather than silently dropping files.
    for key in winners:
        parts=key.split("/")
        if any("/".join(parts[:i]) in winners for i in range(1,len(parts))):raise ValueError("file/directory collision")
    out.mkdir(parents=True,exist_ok=False)
    try:
        for key,p in sorted(winners.items()):
            dest=out.joinpath(*key.split("/"));dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p,dest)
    except Exception:
        shutil.rmtree(out);raise
    return {"output":str(out),"files":len(winners),"conflicts":{k:v for k,v in providers.items() if len(v)>1},"policy":"isolated lowercase copy; loose assets only, no live game changes"}
