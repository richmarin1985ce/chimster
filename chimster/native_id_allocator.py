"""Classic FO3/FNV full-plugin allocation planning.
Format reference: https://tes5edit.github.io/fopdoc/FalloutNV/Records/TES4.html
No upstream code incorporated.
"""
import struct
from .native_parser import parse,subrecords
from .native_payload_edit import replace
from .native_transactions import revision

def inspect(profile,data):
    if profile not in ("fallout3","new-vegas"):raise ValueError("Unverified allocation profile")
    nodes=parse(profile,data)
    if not nodes or nodes[0].signature!=b"TES4":raise ValueError("Missing header")
    flags=struct.unpack_from("<I",nodes[0].header,8)[0]
    if flags&~1:raise ValueError("Only classic full-slot plugin headers are supported for allocation")
    parts=list(subrecords(profile,nodes[0]))
    headers=[v for k,v in parts if k==b"HEDR"]
    if len(headers)!=1 or len(headers[0])!=12:raise ValueError("Invalid HEDR")
    raw=headers[0]
    version,count,cursor=struct.unpack("<fII",raw)
    masters=[v.rstrip(b"\0").decode("cp1252").casefold() for k,v in parts if k==b"MAST"]
    if len(masters)>253 or len(set(masters))!=len(masters):raise ValueError("Invalid master slots")
    stack=list(nodes[1:]);used=set();actual=0
    while stack:
        n=stack.pop();actual+=1
        if n.signature==b"GRUP":stack.extend(n.children);continue
        fid=struct.unpack_from("<I",n.header,12)[0]
        if not fid or not fid&0xffffff or fid>>24>len(masters) or fid in used:raise ValueError("Invalid or duplicate FormID")
        used.add(fid)
    return {"version":version,"count":count,"actual_count":actual,"next_id":cursor,"masters":masters,"used":used,"raw":raw}

def reserve(profile,data,amount,expected_revision):
    if revision(data)!=expected_revision:raise ValueError("Stale allocation")
    if type(amount)!=int or not 1<=amount<=10000:raise ValueError("Invalid amount")
    info=inspect(profile,data)
    if info["count"]!=info["actual_count"]:raise ValueError("Record count mismatch")
    slot=len(info["masters"])<<24
    cursor=max(0x800,info["next_id"],max((fid&0xffffff for fid in info["used"] if fid>>24==len(info["masters"])),default=0)+1)
    if cursor+amount>0xffffff:raise ValueError("FormID exhaustion")
    ids=[slot|i for i in range(cursor,cursor+amount)]
    raw=info["raw"]
    updated=replace(profile,data,(0,),b"HEDR",0,raw,raw[:8]+struct.pack("<I",cursor+amount),expected_revision)
    return updated,ids
