"""Build BA2 v1 GNRL archives from caller-owned assets and supplied native hashes."""
import struct
from .compatibility_asset_lookup import normalize

def build(entries,limit=256*1024*1024):
    rows=[];seen=set();total=24
    for name,data,name_hash,dir_hash in entries:
        key=normalize(name)
        if key in seen:raise ValueError("Duplicate asset")
        seen.add(key)
        raw=key.replace("/",chr(92)).encode("cp1252")
        ext=key.rsplit(".",1)[-1].encode("ascii") if "." in key.rsplit("/",1)[-1] else b""
        if len(ext)>4 or len(raw)>65535 or not isinstance(data,bytes):raise ValueError("Invalid member")
        if not all(isinstance(h,int) and 0<=h<=0xffffffff for h in (name_hash,dir_hash)):raise ValueError("Invalid native hash")
        total+=36+len(data)+2+len(raw)
        if total>limit:raise ValueError("Archive exceeds budget")
        rows.append((raw,ext,data,name_hash,dir_hash))
    offset=24+36*len(rows);records=[];payload=[];names=[]
    for name,ext,data,nh,dh in rows:
        records.append(struct.pack("<I4sIIQIII",nh,ext,dh,0,offset,0,len(data),0xbaadf00d))
        payload.append(data);offset+=len(data)
        names.append(struct.pack("<H",len(name))+name)
    return struct.pack("<4sI4sIQ",b"BTDX",1,b"GNRL",len(rows),offset)+b"".join(records+payload+names)
