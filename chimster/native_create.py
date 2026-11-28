"""Original structural writer; no proprietary assets or code.
HEDR reference: https://tes5edit.github.io/fopdoc/FalloutNV/Records/TES4.html
"""
import struct
from .native_parser import parse,subrecords
from .native_id_allocator import reserve,inspect
from .native_payload_edit import replace
from .native_profiles import PROFILES
import hashlib
ALLOWED={b"MISC",b"WEAP",b"ARMO",b"BOOK",b"NOTE",b"ALCH",b"INGR",b"AMMO",b"KEYM",b"CONT",b"STAT"}
def rev(data):return hashlib.sha256(data).hexdigest()
def insert(profile,data,signature,parts,revision,*,header=None):
    if signature not in ALLOWED:raise ValueError("Unsupported top-level type")
    parts=list(parts)
    ids=[v for k,v in parts if k==b"EDID"]
    if len(ids)!=1 or not ids[0].endswith(b"\0") or not ids[0][:-1] or b"\0" in ids[0][:-1]:raise ValueError("Editor ID required")
    nodes=parse(profile,data)
    for group in nodes[1:]:
        if group.signature!=b"GRUP":continue
        for n in group.children:
            if n.signature==signature and any(k==b"EDID" and v.rstrip(b"\0").lower()==ids[0][:-1].lower() for k,v in subrecords(profile,n)):raise ValueError("Duplicate editor ID")
    candidate,allocated=reserve(profile,data,1,revision)
    info=inspect(profile,candidate)
    payload=b""
    for k,v in parts:
        if not isinstance(k,bytes) or len(k)!=4 or k==b"XXXX" or not isinstance(v,bytes):raise ValueError("Invalid subrecord")
        if len(v)>65535:payload+=struct.pack("<4sHI",b"XXXX",4,len(v))+struct.pack("<4sH",k,0)+v
        else:payload+=struct.pack("<4sH",k,len(v))+v
    if len(payload)>64*1024*1024:raise ValueError("Payload too large")
    h=bytearray(header if header is not None else bytes(PROFILES[profile].record_header))
    if len(h)!=PROFILES[profile].record_header:raise ValueError("Invalid header")
    flags=struct.unpack_from("<I",h,8)[0]
    if flags&0x20:raise ValueError("Deleted source")
    struct.pack_into("<4sIII",h,0,signature,len(payload),flags&~0x40000,allocated[0])
    record=bytes(h)+payload
    nodes=parse(profile,candidate)
    matches=[i for i,n in enumerate(nodes) if n.signature==b"GRUP" and n.header[8:12]==signature and struct.unpack_from("<i",n.header,12)[0]==0]
    if len(matches)>1:raise ValueError("Ambiguous group")
    chunks=[n.header+n.payload for n in nodes]
    if matches:
        i=matches[0];n=nodes[i]
        chunks[i]=n.header[:4]+struct.pack("<I",len(chunks[i])+len(record))+n.header[8:]+n.payload+record
    else:
        gh=PROFILES[profile].group_header
        chunks.append(struct.pack("<4sI4si",b"GRUP",gh+len(record),signature,0)+bytes(gh-16)+record)
    result=b"".join(chunks)
    raw=info["raw"]
    result=replace(profile,result,(0,),b"HEDR",0,raw,raw[:4]+struct.pack("<I",info["count"]+1+int(not matches))+raw[8:],rev(result))
    check=inspect(profile,result)
    if check["count"]!=check["actual_count"] or allocated[0] not in check["used"]:raise ValueError("Creation verification failed")
    return result

def duplicate(profile,data,path,new_id,revision):
    if len(path)!=2:raise ValueError("Only top-level objects supported")
    nodes=parse(profile,data)
    g=nodes[path[0]];n=g.children[path[1]]
    if g.signature!=b"GRUP" or g.header[8:12]!=n.signature or struct.unpack_from("<i",g.header,12)[0]!=0:raise ValueError("Invalid source group")
    if not isinstance(new_id,str) or not new_id.strip() or "\0" in new_id:raise ValueError("Invalid editor ID")
    parts=[(k,new_id.encode("cp1252")+b"\0" if k==b"EDID" else v) for k,v in subrecords(profile,n)]
    return insert(profile,data,n.signature,parts,revision,header=n.header)
