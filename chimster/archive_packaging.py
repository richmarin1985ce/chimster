"""Experimental BA2 packaging for original assets with supplied native hashes."""
import io,os,tempfile
from pathlib import Path
from . import ba2_writer,ba2_general
from .compatibility_asset_lookup import normalize

def package(destination,entries,*,compress=True,limit=256*1024*1024):
    rows=list(entries)
    data=ba2_writer.build(rows,limit=limit,compress=compress)
    stream=io.BytesIO(data)
    directory=ba2_general.directory(stream)
    if len(directory)!=len(rows):raise ValueError("Directory verification failed")
    for name,raw,_,_ in rows:
        if ba2_general.read(stream,directory[normalize(name)],limit)!=raw:
            raise ValueError("Payload verification failed: "+name)
    target=Path(destination)
    if target.suffix.lower()!=".ba2":raise ValueError("Expected BA2 destination")
    fd,temp=tempfile.mkstemp(prefix=".chimster-",dir=target.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(data);out.flush();os.fsync(out.fileno())
        os.link(temp,target)
    finally:
        os.unlink(temp)
    return {"path":str(target),"members":len(rows),"bytes":len(data),"roundtrip_verified":True,"retail_verified":False}

def package_assets(destination,entries,**options):
    from .ba2_hash import prepare
    return package(destination,prepare(entries),**options)

def package_directory(source,destination,*,compress=True,limit=256*1024*1024):
    root=Path(source).resolve()
    if not root.is_dir():raise ValueError("Expected asset directory")
    if Path(destination).resolve().is_relative_to(root):raise ValueError("Save archive outside source directory")
    def assets():
        total=0
        for path in sorted(root.rglob("*")):
            if path.is_symlink():raise ValueError("Symlinks are not supported")
            if not path.is_file():continue
            if not path.resolve().is_relative_to(root):raise ValueError("Asset outside source directory")
            name=path.relative_to(root).as_posix()
            total+=path.stat().st_size+36+2+len(name.encode("ascii"))
            if total+24>limit:raise ValueError("Asset directory exceeds budget")
            with path.open("rb") as stream:
                raw=stream.read(limit-total+path.stat().st_size+1)
            if len(raw)!=path.stat().st_size:raise ValueError("Asset changed during read")
            yield name,raw
    return package_assets(destination,assets(),compress=compress,limit=limit)
