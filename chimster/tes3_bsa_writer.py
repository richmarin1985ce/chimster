"""TES3 archive writer. Format reference: xEdit Core/wbHash.pas (TES3 hash).
Original Python implementation, ASCII paths only.
"""
import struct
from .compatibility_asset_lookup import normalize
MASK=0xffffffff

def native_hash(name):
    raw=normalize(name).replace("/",chr(92)).encode("ascii")
    half=len(raw)//2
    low=0;high=0
    for i,b in enumerate(raw[:half]):
        low^=b<<(8*(i%4))
    for i,b in enumerate(raw[half:]):
        word=b<<(8*(i%4))
        high^=word
        shift=word&31
        high=((high>>shift)|(high<<(32-shift)))&MASK
    return low|(high<<32)

def build(entries,limit=256*1024*1024):
    rows=[];seen=set();total=12
    for name,data in entries:
        key=normalize(name)
        h=native_hash(key)
        if h in seen:raise ValueError("Duplicate path or native hash collision")
        seen.add(h)
        raw=key.replace("/",chr(92)).encode("ascii")+b"\0"
        if not isinstance(data,bytes):raise ValueError("Expected binary asset")
        total+=20+len(raw)+len(data)
        if total>min(limit,0xffffffff) or len(rows)>=1000000:raise ValueError("Archive exceeds budget")
        rows.append((h,raw,data))
    rows.sort(key=lambda row:row[0])
    records=[];offsets=[];names=[];hashes=[];payload=[]
    n=0;p=0
    for h,name,data in rows:
        records.append(struct.pack("<II",len(data),p))
        offsets.append(struct.pack("<I",n))
        names.append(name);hashes.append(struct.pack("<Q",h));payload.append(data)
        n+=len(name);p+=len(data)
    return struct.pack("<III",0x100,12*len(rows)+n,len(rows))+b"".join(records+offsets+names+hashes+payload)
