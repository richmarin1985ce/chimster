"""Bounded typed replacement; preserve untouched subrecord framing."""
import struct
import zlib
from .native_parser import subrecords
from .native_catalog import CATALOGS, references
from .native_profiles import PROFILES
from dataclasses import replace

def edit_reference(profile,node,slots,index,expected,target,record_types):
    if PROFILES[profile].family=="TES3":
        raise ValueError("TES3 reference editing unsupported")
    sig=node.signature.decode("ascii")
    parts=list(subrecords(profile,node))
    if not 0<=index<len(parts):
        raise ValueError("missing field")
    tag,raw=parts[index]
    spec=CATALOGS[profile].get((sig,tag))
    if spec is None or len(raw)!=spec.length:
        raise ValueError("unknown field layout")
    if slots.decode(struct.unpack_from("<I",raw,spec.offset)[0])!=expected:
        raise ValueError("stale reference")
    if target is not None and (target not in record_types or
        spec.targets and record_types[target] not in spec.targets):
        raise ValueError("unresolved or wrong-type target")
    compressed=bool(struct.unpack_from("<I",node.header,8)[0]&0x40000)
    data=bytearray(zlib.decompress(node.payload[4:]) if compressed else node.payload)
    pos=0
    extended=None
    i=0
    while pos<len(data):
        t,n=struct.unpack_from("<4sH",data,pos)
        pos+=6
        if t==b"XXXX":
            extended=struct.unpack_from("<I",data,pos)[0]
            pos+=4
            continue
        if extended is not None:
            n,extended=extended,None
        if i==index:
            struct.pack_into("<I",data,pos+spec.offset,slots.encode(target))
            break
        pos+=n
        i+=1
    payload=struct.pack("<I",len(data))+zlib.compress(data) if compressed else bytes(data)
    result=replace(node,payload=payload)
    list(subrecords(profile,result))
    return result

def semantic_fields(profile,node,slots):
    """Compare known references by origin; retain all other bytes."""
    parts=list(subrecords(profile,node))
    edges,opaque=references(profile,node.signature.decode("ascii"),parts,slots)
    normalized=[]
    for i,(tag,raw) in enumerate(parts):
        value=bytearray(raw)
        targets=[]
        for field,offset,target,_ in edges:
            if field==i:
                value[offset:offset+4]=bytes(4)
                targets.append((offset,target))
        normalized.append((tag,bytes(value),tuple(targets)))
    return tuple(normalized),tuple(opaque)
