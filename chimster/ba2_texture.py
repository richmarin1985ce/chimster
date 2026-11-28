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
    if magic!=b"BTDX" or version not in (1,7,8) or kind!=b"DX10":raise ValueError("Unsupported texture archive")
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

# Standard DXGI BC formats and their bytes per 4x4 block.
BLOCKS={71:8,72:8,74:16,75:16,77:16,78:16,80:8,81:8,83:16,84:16,95:16,96:16,98:16,99:16}

def read(stream,entry,limit=64*1024*1024):
    import zlib
    w,h,mips,fmt=(entry[k] for k in ("width","height","mips","dxgi_format"))
    cube=bool(entry["flags"]&1)
    if cube and (w!=h or len(entry["chunks"])!=1):raise ValueError("Unsupported cubemap layout")
    if entry["flags"]&~1 or fmt not in BLOCKS or not 1<=mips<=max(w,h).bit_length():
        raise ValueError("Unsupported DDS texture layout")
    sizes=[max(1,((max(1,w>>i)+3)//4))*max(1,((max(1,h>>i)+3)//4))*BLOCKS[fmt] for i in range(mips)]
    if sum(sizes)*(6 if cube else 1)+148>limit:raise ValueError("Texture exceeds limit")
    chunks=sorted(entry["chunks"],key=lambda c:c["first_mip"])
    parts=[];next_mip=0
    for chunk in chunks:
        first,last=chunk["first_mip"],chunk["last_mip"]
        expected=sum(sizes[first:last+1])*(6 if cube else 1)
        if first!=next_mip or last>=mips or chunk["unpacked"]!=expected or chunk["packed"]>limit:
            raise ValueError("Invalid mip coverage or size")
        stream.seek(chunk["offset"])
        raw=exact(stream,chunk["packed"] or expected)
        if chunk["packed"]:
            dec=zlib.decompressobj();raw=dec.decompress(raw,expected+1)
            if not dec.eof or dec.unused_data or dec.unconsumed_tail:raise ValueError("Invalid texture compression")
        if len(raw)!=expected:raise ValueError("Invalid chunk size")
        parts.append(raw);next_mip=last+1
    if next_mip!=mips:raise ValueError("Incomplete mip chain")
    flags=0x81007|(0x20000 if mips>1 else 0)
    caps=0x1000|(0x400008 if mips>1 else 0)
    header=struct.pack("<7I11I",124,flags,h,w,sizes[0],0,mips,*([0]*11))
    pixel=struct.pack("<II4s5I",32,4,b"DX10",0,0,0,0,0)
    return b"DDS "+header+pixel+struct.pack("<5I",caps|(8 if cube else 0),0xfe00 if cube else 0,0,0,0)+struct.pack("<5I",fmt,3,4 if cube else 0,1,0)+b"".join(parts)
