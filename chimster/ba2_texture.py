"""Read-only BA2 v1 DX10 metadata; no DDS reconstruction yet."""
import struct
from .compatibility_asset_lookup import normalize

def exact(stream,n):
    data=stream.read(n)
    if len(data)!=n:raise ValueError("Truncated texture archive")
    return data

def directory(stream):
    stream.seek(0,2);size=stream.tell();stream.seek(0)
    magic,version,kind,count,names=struct.unpack("<4sI4sIQ",exact(stream,24))
    if (magic,version,kind)!=(b"BTDX",1,b"DX10"):raise ValueError("Unsupported texture archive")
    if count>1000000 or not 24+24*count<=names<=size:raise ValueError("Invalid directory extent")
    rows=[]
    for _ in range(count):
        if stream.tell()+24>names:raise ValueError("Invalid texture directory")
        _,ext,_,unknown,nchunks,chunk_size,height,width,mips,fmt,flags=struct.unpack("<I4sIBBHHHBBH",exact(stream,24))
        if chunk_size!=24 or not nchunks or not width or not height or not mips:raise ValueError("Unsupported texture layout")
        if stream.tell()+24*nchunks>names:raise ValueError("Invalid chunk directory")
        chunks=[]
        for _ in range(nchunks):
            offset,packed,unpacked,first,last,marker=struct.unpack("<QIIHHI",exact(stream,24))
            if first>last or last>=mips or offset+(packed or unpacked)>names:raise ValueError("Invalid texture chunk")
            chunks.append({"offset":offset,"packed":packed,"unpacked":unpacked,"first_mip":first,"last_mip":last})
        rows.append({"width":width,"height":height,"mips":mips,"dxgi_format":fmt,"flags":flags,"chunks":chunks})
    end=stream.tell()
    if any(c["offset"]<end for row in rows for c in row["chunks"]):raise ValueError("Chunk overlaps directory")
    stream.seek(names);result={}
    for row in rows:
        length=struct.unpack("<H",exact(stream,2))[0]
        name=normalize(exact(stream,length).decode("cp1252"))
        if name in result:raise ValueError("Duplicate texture")
        result[name]=row
    return result
