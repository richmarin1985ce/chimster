"""Independent read-only BA2 v1 GNRL reader. DX10 and newer versions fail closed."""
import struct,zlib
from .compatibility_asset_lookup import normalize

def directory(stream):
    stream.seek(0,2);size=stream.tell();stream.seek(0)
    header=stream.read(24)
    if len(header)!=24:raise ValueError("Truncated BA2")
    magic,version,kind,count,names=struct.unpack("<4sI4sIQ",header)
    if (magic,version,kind)!=(b"BTDX",1,b"GNRL"):raise ValueError("Unsupported BA2 variant")
    if count>1000000 or not 24+36*count<=names<=size:raise ValueError("Invalid directory extent")
    rows=[]
    for _ in range(count):
        raw=stream.read(36)
        if len(raw)!=36:raise ValueError("Truncated entry")
        _,_,_,_,offset,packed,unpacked,_=struct.unpack("<I4sIIQIII",raw)
        length=packed or unpacked
        if offset<24+36*count or offset+length>names:raise ValueError("Invalid member extent")
        rows.append((offset,packed,unpacked))
    stream.seek(names);result={}
    for row in rows:
        raw=stream.read(2)
        if len(raw)!=2:raise ValueError("Truncated name length")
        n=struct.unpack("<H",raw)[0];raw=stream.read(n)
        if len(raw)!=n:raise ValueError("Truncated name")
        name=normalize(raw.decode("cp1252"))
        if name in result:raise ValueError("Duplicate member")
        result[name]=row
    return result

def read(stream,entry,limit=64*1024*1024):
    offset,packed,unpacked=entry
    if min(offset,packed,unpacked)<0 or max(packed,unpacked)>limit:raise ValueError("Member exceeds limit")
    stream.seek(offset);raw=stream.read(packed or unpacked)
    if len(raw)!=(packed or unpacked):raise ValueError("Truncated member")
    if not packed:return raw
    dec=zlib.decompressobj();out=dec.decompress(raw,unpacked+1)
    if len(out)!=unpacked or not dec.eof or dec.unused_data or dec.unconsumed_tail:raise ValueError("Invalid compressed member")
    return out
