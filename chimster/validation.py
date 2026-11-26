"""Overlay asset index and deterministic reference audit (loose files only)."""
from pathlib import Path,PurePosixPath
from hashlib import sha256
def normalize(path):
    if not isinstance(path,str):raise ValueError("invalid asset path")
    p=PurePosixPath(path.replace("\\","/"))
    if p.is_absolute() or ".." in p.parts or ":" in str(p) or not p.parts:raise ValueError("unsafe asset path")
    return p.as_posix().casefold()
def index_assets(dirs):
    result={}
    for directory in dirs:
        root=Path(directory).resolve(strict=True)
        if not root.is_dir():raise ValueError("expected data directory")
        seen=set()
        for p in sorted(root.rglob("*")):
            if p.is_symlink() or not p.is_file():continue
            key=normalize(p.relative_to(root).as_posix())
            if key in seen:raise ValueError("case collision "+key)
            seen.add(key);result.setdefault(key,[]).append(str(p))
    return result
def audit_assets(index,references):
    rows=[]
    for r in references:
        key=normalize(r["path"]);chain=index.get(key,[])
        rows.append({"owner":r["owner"],"path":r["path"],"status":"present" if chain else "missing-loose-file","winner":chain[-1] if chain else None,"providers":chain})
    return rows
