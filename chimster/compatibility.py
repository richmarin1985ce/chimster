"""Read-only release inventory and conservative format capability routing.
No game process, network, authentication, server or installation access."""
from pathlib import Path
import hashlib,struct,json
from .core import inspect_plugin

CAPABILITIES={
 "oblivionremastered":{"legacy_records":"structural inspection; xEdit TES4R separately installed","unreal_assets":"inventory and staged package layout only","write":"unverified","online":False},
 "fallout76":{"legacy_records":"structural inspection only","unreal_assets":"not applicable","write":"disabled","online":True},
}
def archive_header(p):
    p=Path(p)
    with p.open("rb") as f:raw=f.read(36)
    if p.suffix.lower()==".ba2":
        if len(raw)<24 or raw[:4]!=b"BTDX":raise ValueError("invalid BA2 header")
        version,kind,count,offset=struct.unpack_from("<I4sIQ",raw,4)
        header={1:24,2:32,3:36,7:24,8:24}.get(version)
        known=header is not None and kind in (b"GNRL",b"DX10")
        if known and (len(raw)<header or not header<=offset<=p.stat().st_size):raise ValueError("invalid BA2 name table offset")
        return {"format":"BA2","version":version,"kind":kind.decode("ascii",errors="replace"),"entries":count,"name_table_offset":offset,"recognized_layout":known}
    if p.suffix.lower()==".bsa":
        if len(raw)<8:raise ValueError("short BSA")
        return {"format":"BSA","magic":raw[:4].hex(),"version_word":struct.unpack_from("<I",raw,4)[0],"recognized_layout":False}
    raise ValueError("not a Bethesda archive")
def inspect(path,game):
    if game not in CAPABILITIES:raise ValueError("unsupported compatibility profile")
    p=Path(path);ext=p.suffix.lower()
    if ext in {".esp",".esm",".esl"}:
        candidates=("oblivion","oblivionremastered") if game=="oblivionremastered" else ("fallout4",)
        results=[]
        for candidate in candidates:
            try:results.append(inspect_plugin(p,candidate))
            except (OSError,ValueError,struct.error):pass
        if len(results)!=1:return {"format":"TES4","status":"unknown or ambiguous structural layout","candidate_count":len(results),"writes_allowed":False}
        result=results[0];return {"format":"TES4","status":"structural layout recognized, semantic schema unverified","layout_profile":result["game"],"masters":result["masters"],"record_counts":result["record_counts"],"writes_allowed":False}
    if ext in {".ba2",".bsa"}:return {**archive_header(p),"writes_allowed":False}
    if game=="oblivionremastered" and ext in {".pak",".ucas",".utoc"}:
        return {"format":ext[1:].upper(),"status":"container type by extension only","writes_allowed":False}
    return {"format":"unknown","writes_allowed":False}
def layout(root):
    root=Path(root).resolve(strict=True)
    data=root/"OblivionRemastered"/"Content"/"Dev"/"ObvData"/"Data"
    paks=root/"OblivionRemastered"/"Content"/"Paks"
    return {"data":str(data),"data_present":data.is_dir(),"paks":str(paks),"paks_present":paks.is_dir(),"mods":str(paks/"~mods"),"status":"candidate layout; verify installation root"}
def remaster_package(paths):
    """Classify explicitly selected package files; never install them."""
    result=[];sets={}
    for p in map(Path,paths):
        if p.is_symlink() or not p.is_file():raise ValueError("expected regular package file")
        ext=p.suffix.lower()
        if ext in {".esm",".esp",".esl",".bsa"}:destination="OblivionRemastered/Content/Dev/ObvData/Data"
        elif ext in {".pak",".ucas",".utoc"}:
            destination="OblivionRemastered/Content/Paks/~mods"
            sets.setdefault(p.stem.casefold(),set()).add(ext)
        else:raise ValueError("unsupported package file")
        result.append({"source":str(p),"destination":destination+"/"+p.name})
    if len({r["destination"].casefold() for r in result})!=len(result):raise ValueError("duplicate destination")
    warnings=[name for name,types in sets.items() if bool(types&{".ucas",".utoc"}) and not {".ucas",".utoc"}<=types]
    return {"files":result,"incomplete_iostore_pairs":warnings,"status":"review only; no installation","writes_allowed":False}
def snapshot(root,game,release):
    if game not in CAPABILITIES or not isinstance(release,str) or not 1<=len(release)<=128:raise ValueError("invalid release")
    root=Path(root).resolve(strict=True)
    if not root.is_dir():raise ValueError("expected directory")
    files={}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():continue
        if not p.is_file() or p.suffix.lower() not in {".esp",".esm",".esl",".ba2",".bsa",".pak",".ucas",".utoc",".exe"}:continue
        if not p.resolve().is_relative_to(root):raise ValueError("file outside root")
        if len(files)>=10000:raise ValueError("inventory limit")
        name=p.relative_to(root).as_posix()
        if name.casefold() in {k.casefold() for k in files}:raise ValueError("case collision")
        size=p.stat().st_size
        # Bounded sample is a change hint, not a full-content digest.
        with p.open("rb") as f:
            h=hashlib.sha256(f.read(65536))
            if size>65536:f.seek(max(65536,size-65536));h.update(f.read(65536))
        files[name]={"bytes":size,"sample_sha256":h.hexdigest()}
    return {"schema":1,"game":game,"release":release,"files":files,"status":"sampled inventory; new versions need explicit schema testing"}
def compare(old,new):
    if old.get("schema")!=1 or new.get("schema")!=1 or old.get("game")!=new.get("game"):raise ValueError("incompatible snapshots")
    a,b=old["files"],new["files"]
    return {"added":sorted(set(b)-set(a)),"removed":sorted(set(a)-set(b)),"changed":sorted(k for k in set(a)&set(b) if a[k]!=b[k]),"release_changed":old["release"]!=new["release"],"native_write_approved":False,"warning":"Sample hashes cannot prove entire files unchanged; validate formats before enabling writers."}
