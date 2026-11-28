"""Conservative initial creation templates; not retail-certified."""
import struct
import hashlib
from .native_parser import parse,subrecords
from .native_payload_edit import replace
from .tes3_items import edit_properties,SCHEMAS

def create(data,signature,new_id,name,revision,*,model,properties=None):
    if hashlib.sha256(data).hexdigest()!=revision:raise ValueError("Stale revision")
    if signature not in ("MISC","WEAP","ARMO","CLOT","ALCH"):raise ValueError("Unsupported creation template")
    def encode(value,limit):
        if not isinstance(value,str) or not value.strip() or "\0" in value:raise ValueError("Invalid text")
        raw=value.encode("cp1252")
        if len(raw)>limit:raise ValueError("Text too long")
        return raw+b"\0"
    identity=encode(new_id,31)
    parts=[(b"NAME",identity),(b"MODL",encode(model,255)),(b"FNAM",encode(name,255))]
    tag={"MISC":"MCDT","WEAP":"WPDT","ARMO":"AODT","CLOT":"CTDT","ALCH":"ALDT"}[signature]
    fmt,keys=SCHEMAS[signature,tag]
    values=dict.fromkeys(keys,0)
    for key in ("speed","reach"):
        if key in values:values[key]=1
    raw=edit_properties(signature,tag,struct.pack(fmt,*(values[k] for k in keys)),**(properties or {}))
    parts.append((tag.encode(),raw))
    nodes=parse("morrowind",data)
    if not nodes or nodes[0].signature!=b"TES3":raise ValueError("Missing header")
    for node in nodes[1:]:
        if node.signature==signature.encode():
            if any(k==b"NAME" and v.rstrip(b"\0").decode("cp1252").casefold()==new_id.casefold() for k,v in subrecords("morrowind",node)):raise ValueError("Duplicate local ID")
    headers=[v for k,v in subrecords("morrowind",nodes[0]) if k==b"HEDR"]
    if len(headers)!=1 or len(headers[0])!=300:raise ValueError("Unsupported header")
    h=headers[0];count=struct.unpack_from("<I",h,296)[0]
    if count!=len(nodes)-1:raise ValueError("Header count mismatch")
    payload=b"".join(struct.pack("<4sI",k,len(v))+v for k,v in parts)
    result=replace("morrowind",data,(0,),b"HEDR",0,h,h[:296]+struct.pack("<I",count+1),revision)+struct.pack("<4sIII",signature.encode(),len(payload),0,0)+payload
    parse("morrowind",result)
    return result
