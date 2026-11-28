"""BA2 v1 DX10 writer for supported single-surface BC DDS assets."""
import struct,zlib
from .dds_texture import parse
from .ba2_hash import hashes
from .compatibility_asset_lookup import normalize

def build(entries,limit=256*1024*1024,compress=True,*,version=1):
    if version not in (1,7,8):raise ValueError('Unsupported Fallout 4 BA2 version')
    rows=[];seen=set();total=24
    for name,data in entries:
        key=normalize(name)
        if not key.endswith(".dds"):raise ValueError("Expected DDS asset")
        nh,dh=hashes(key)
        if (nh,dh) in seen:raise ValueError("Duplicate or hash collision")
        seen.add((nh,dh))
        texture=parse(data)
        raw=b"".join(texture["levels"])
        candidate=zlib.compress(raw) if compress else raw
        packed=len(candidate) if compress and len(candidate)<len(raw) else 0
        stored=candidate if packed else raw
        path=key.replace("/",chr(92)).encode("ascii")
        total+=48+2+len(path)+len(raw)
        if len(path)>65535 or total>limit or len(rows)>=1000000:raise ValueError("Archive exceeds budget")
        rows.append((nh,dh,path,texture,raw,stored,packed))
    offset=24+48*len(rows);records=[];payload=[];names=[]
    for nh,dh,path,t,raw,stored,packed in rows:
        records.append(struct.pack("<I4sIBBHHHBBH",nh,b"dds",dh,0,1,24,t["height"],t["width"],t["mips"],t["dxgi_format"],int(t["cubemap"])))
        records.append(struct.pack("<QIIHHI",offset,packed,len(raw),0,t["mips"]-1,0xbaadf00d))
        payload.append(stored);offset+=len(stored)
        names.append(struct.pack("<H",len(path))+path)
    return struct.pack("<4sI4sIQ",b"BTDX",version,b"DX10",len(rows),offset)+b"".join(records+payload+names)
