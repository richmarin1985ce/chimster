"""Experimental classic BSA writer.
Format facts: TES5Edit Core/wbBSArchive.pas, folder offsets include filename table length.
"""
import struct,zlib
from .classic_bsa_hash import native_hash
from .compatibility_asset_lookup import normalize

def build(entries,limit=256*1024*1024,*,version=103,compress=False):
    if version not in (103,104,105):raise ValueError('Unsupported BSA version')
    stride=24 if version==105 else 16
    groups={};seen=set();total=36
    for name,data in entries:
        key=normalize(name)
        folder,sep,leaf=key.rpartition("/")
        if not sep or not isinstance(data,bytes):raise ValueError("Expected folder and binary asset")
        f=folder.replace("/",chr(92)).encode("ascii")+b"\0"
        n=leaf.encode("ascii")+b"\0"
        if len(f)>255 or len(data)>=0x40000000:raise ValueError("Unsupported member size")
        fh=native_hash(folder);nh=native_hash(leaf,True)
        if (fh,nh) in seen:raise ValueError("Duplicate or hash collision")
        seen.add((fh,nh))
        if fh not in groups:
            groups[fh]=(f,[])
            total+=stride+1+len(f)
        if groups[fh][0]!=f:raise ValueError("Folder hash collision")
        groups[fh][1].append((nh,n,data))
        total+=16+len(n)+len(data)
        if total>min(limit,0xffffffff) or len(seen)>1000000:raise ValueError("Archive exceeds budget")
    ordered=sorted(groups.items())
    folder_len=sum(len(f) for _,(f,_) in ordered)
    name_len=sum(len(n) for _,(_,rows) in ordered for _,n,_ in rows)
    cursor=36+stride*len(ordered)
    pos=cursor+len(ordered)+folder_len+16*len(seen)+name_len
    headers=[];blocks=[];names=[];payload=[]
    for fh,(f,rows) in ordered:
        headers.append(struct.pack("<QIIQ",fh,len(rows),0,cursor+name_len) if version==105 else struct.pack("<QII",fh,len(rows),cursor+name_len))
        blocks.append(bytes([len(f)])+f)
        cursor+=1+len(f)+16*len(rows)
        for nh,n,data in sorted(rows):
            stored=data;flag=0
            if compress and data:
                if version==105:
                    try:from lz4.frame import compress as encode
                    except ImportError as exc:raise ValueError("LZ4 support is not installed") from exc
                else:encode=zlib.compress
                candidate=struct.pack("<I",len(data))+encode(data)
                if len(candidate)<len(data):
                    stored=candidate;flag=0x40000000
            blocks.append(struct.pack("<QII",nh,len(stored)|flag,pos))
            names.append(n);payload.append(stored);pos+=len(stored)
    return struct.pack("<4s8I",b"BSA\0",version,36,3,len(ordered),len(seen),folder_len,name_len,0)+b"".join(headers+blocks+names+payload)
