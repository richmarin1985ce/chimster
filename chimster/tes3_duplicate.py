"""Duplicate supported named TES3 records without changing their source."""
import hashlib
import struct
from .native_parser import parse,subrecords
from .tes3_items import ITEMS
from .native_payload_edit import replace

def duplicate(data,index,new_id,revision):
    if hashlib.sha256(data).hexdigest()!=revision:raise ValueError("Stale revision")
    if not isinstance(new_id,str) or not new_id.strip() or "\0" in new_id:raise ValueError("Invalid ID")
    encoded=new_id.encode("cp1252")
    if len(encoded)>31:raise ValueError("ID exceeds conservative 31-byte limit")
    nodes=parse("morrowind",data)
    if type(index)!=int or not 0<index<len(nodes):raise ValueError("Invalid source")
    source=nodes[index]
    if source.signature not in ITEMS:raise ValueError("Unsupported duplication type")
    parts=list(subrecords("morrowind",source))
    names=[v for k,v in parts if k==b"NAME"]
    if len(names)!=1 or any(k==b"DELE" for k,v in parts):raise ValueError("Invalid source identity")
    for node in nodes[1:]:
        if node.signature not in ITEMS:continue
        for k,v in subrecords("morrowind",node):
            if k==b"NAME" and v.rstrip(b"\0").decode("cp1252").casefold()==new_id.casefold():
                raise ValueError("Duplicate local identity")
    raw=source.header+source.payload
    clone=replace("morrowind",raw,(0,),b"NAME",0,names[0],encoded+b"\0",hashlib.sha256(raw).hexdigest())
    if nodes[0].signature!=b"TES3":raise ValueError("Missing header")
    headers=[v for k,v in subrecords("morrowind",nodes[0]) if k==b"HEDR"]
    if len(headers)!=1 or len(headers[0])!=300:raise ValueError("Unsupported header")
    h=headers[0]
    count=struct.unpack_from("<I",h,296)[0]
    if count!=len(nodes)-1:raise ValueError("Header count mismatch")
    updated=replace("morrowind",data,(0,),b"HEDR",0,h,h[:296]+struct.pack("<I",count+1),revision)
    result=updated+clone
    parse("morrowind",result)
    return result
