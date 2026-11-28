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
