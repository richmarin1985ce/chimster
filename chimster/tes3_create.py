"""Conservative initial creation templates; not retail-certified."""
import struct
import hashlib
from .native_parser import parse,subrecords
from .native_payload_edit import replace
from .tes3_items import edit_properties,SCHEMAS,edit_book_data,edit_ingredient,edit_magic_effect,edit_container_flags,edit_leveled_level,edit_chance_none,ITEMS

def create(data,signature,new_id,name,revision,*,model=None,properties=None,body='',effects=(),entries=(),actor_fields=None,ai_packages=()):
    if hashlib.sha256(data).hexdigest()!=revision:raise ValueError("Stale revision")
    if signature.encode("ascii") not in ITEMS:raise ValueError("Unsupported creation template")
    def encode(value,limit):
        if not isinstance(value,str) or not value.strip() or "\0" in value:raise ValueError("Invalid text")
        raw=value.encode("cp1252")
        if len(raw)>limit:raise ValueError("Text too long")
        return raw+b"\0"
    identity=encode(new_id,31)
    parts=[(b"NAME",identity)]
    props=dict(properties or {})
    if signature not in ("SPEL","ENCH","LEVI","LEVC"):
        parts.append((b"MODL",encode(model,255)))
    if signature not in ("ENCH","LEVI","LEVC"):
        parts.append((b"FNAM",encode(name,255)))
    schemas={s:t for s,t in SCHEMAS}
    if signature in schemas:
        tag=schemas[signature]
        fmt,keys=SCHEMAS[signature,tag]
        values=dict.fromkeys(keys,0)
        for key in ("speed","reach","quality"):
            if key in values:values[key]=1
        if signature=="CONT":
            flags=props.pop("container_flags",{})
        raw=edit_properties(signature,tag,struct.pack(fmt,*(values[k] for k in keys)),**props)
        parts.append((tag.encode(),raw))
        if signature=="CONT":
            parts.append((b"FLAG",edit_container_flags(struct.pack("<I",8),**flags)))
    elif signature=="BOOK":
        parts.extend([(b"BKDT",edit_book_data(struct.pack("<fIIiI",0,0,0,-1,0),**props)),(b"TEXT",body.encode("cp1252")+b"\0")])
    elif signature=="INGR":
        parts.append((b"IRDT",edit_ingredient(struct.pack("<fi12i",0,0,*([-1]*12)),**props)))
    elif signature in ("LEVI","LEVC"):
        flags=props.pop("flags",0);chance=props.pop("chance_none",0)
        if props or type(flags)!=int or not 0<=flags<=0xffffffff:raise ValueError("Invalid list properties")
        entries=list(entries)
        parts.extend([(b"DATA",struct.pack("<I",flags)),(b"NNAM",edit_chance_none(b"\0",chance)),(b"INDX",struct.pack("<I",len(entries)))])
        for item,level in entries:
            parts.extend([(b"INAM" if signature=="LEVI" else b"CNAM",encode(item,31)),(b"INTV",edit_leveled_level(bytes(2),level))])
    elif signature in ("NPC_","CREA"):
        # Explicit native actor data required: never invent race/class/stats.
        fields=list(actor_fields or ())
        allowed={b"RNAM",b"CNAM",b"ANAM",b"BNAM",b"KNAM",b"NPDT",b"FLAG",b"AIDT",b"NPCO",b"NPCS",b"SCRI",b"XSCL"}
        if props or any(k not in allowed or not isinstance(v,bytes) for k,v in fields):raise ValueError("Invalid actor fields")
        stats=[v for k,v in fields if k==b"NPDT"]
        if len(stats)!=1 or len(stats[0]) not in ((12,52) if signature=="NPC_" else (96,)):raise ValueError("Explicit actor stats required")
        required={b"FLAG",b"AIDT"} | ({b"RNAM",b"CNAM",b"ANAM",b"BNAM",b"KNAM"} if signature=="NPC_" else set())
        if any(sum(k==tag for k,v in fields)!=1 for tag in required):raise ValueError("Missing or duplicate actor field")
        parts.extend(fields)
        from .tes3_ai_packages import encode_package
        for package in ai_packages:
            parts.extend(encode_package(**package))
    else:raise ValueError("Unsupported creation template")
    if signature in ("SPEL","ENCH","ALCH"):
        for effect in effects:
            parts.append((b"ENAM",edit_magic_effect(struct.pack("<Hbb5i",0,-1,-1,0,0,0,0,0),**effect)))
        if not effects:raise ValueError("At least one effect required")
    elif effects:raise ValueError("Effects unsupported")
    if signature=="CONT":
        for item,count in entries:
            if type(count)!=int or not -2147483648<=count<=2147483647:raise ValueError("Invalid inventory count")
            parts.append((b"NPCO",struct.pack("<i32s",count,encode(item,31))))
    if ai_packages and signature not in ("NPC_","CREA"):raise ValueError("AI packages require actor")
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
