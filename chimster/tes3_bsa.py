"""Independent TES3 BSA reader; offsets relative to file data area."""
import struct
from .compatibility_asset_lookup import normalize

def directory(stream):
    stream.seek(0,2);size=stream.tell();stream.seek(0)
    header=stream.read(12)
    if len(header)!=12:raise ValueError("Truncated header")
    magic,hash_offset,count=struct.unpack("<III",header)
    if magic!=0x100 or count>1000000:raise ValueError("Unsupported archive")
    names_start=12+12*count
    hashes=12+hash_offset
    base=hashes+8*count
    if not names_start<=hashes<=base<=size or hashes-names_start>64*1024*1024:raise ValueError("Invalid directory")
    rows=[struct.unpack("<II",stream.read(8)) for _ in range(count)]
    offsets=[struct.unpack("<I",stream.read(4))[0] for _ in range(count)]
    names=stream.read(hashes-names_start);result={}
    for (length,offset),n in zip(rows,offsets):
        end=names.find(b"\0",n)
        if n>=len(names) or end<0 or base+offset+length>size:raise ValueError("Invalid member")
        key=normalize(names[n:end].decode("cp1252"))
        if key in result:raise ValueError("Duplicate member")
        result[key]=(base+offset,length)
    return result

def read(stream,entry,limit=64*1024*1024):
    offset,length=entry
    if offset<0 or not 0<=length<=limit:raise ValueError("Invalid member extent")
    stream.seek(offset);data=stream.read(length)
    if len(data)!=length:raise ValueError("Truncated member")
    return data
