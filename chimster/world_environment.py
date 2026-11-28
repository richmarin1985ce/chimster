"""FNV WRLD environmental fields, based on fopdoc FalloutNV/Records/WRLD.html.

Only typed fields below are edited; other subrecords remain unchanged.
"""
import struct
from math import isfinite
from .record_graph import Identity

LINKS={"parent":(b"WNAM","WRLD"),"climate":(b"CNAM","CLMT"),"water":(b"NAM2","WATR"),"lod_water":(b"NAM3","WATR"),
       "image_space":(b"INAM","IMGS"),"music":(b"ZNAM","MUSC"),"encounter_zone":(b"XEZN","ECZN")}
FIELDS={"inheritance":(b"PNAM","<H"),"heights":(b"DNAM","<2f"),"lod_height":(b"NAM4","<f"),
        "map_size_bounds":(b"MNAM","<2i4h"),"map_offset":(b"ONAM","<3f"),"flags":(b"DATA","<B")}
TEXTURES={"map_texture":b"ICON","small_map_texture":b"MICO","canopy_shadow":b"NNAM","water_noise":b"XNAM"}
INHERIT={"heights":1,"lod_height":2,"lod_water":2,"map_size_bounds":4,"map_offset":4,"map_texture":4,"small_map_texture":4,"water":8,"climate":16,"image_space":32}
ORDER=tuple(b"EDID FULL XEZN WNAM PNAM CNAM NAM2 NAM3 NAM4 DNAM ICON MICO MNAM ONAM INAM DATA NAM0 NAM9 ZNAM NNAM XNAM IMPS IMPF OFST".split())

def decode(parts,slots):
    result={}
    for name,(tag,fmt) in FIELDS.items():
        values=[v for t,v in parts if t==tag]
        if len(values)==1 and len(values[0])==struct.calcsize(fmt):
            decoded=struct.unpack(fmt,values[0])
            if all(isfinite(v) for v in decoded):result[name]=decoded
    for name,(tag,_) in LINKS.items():
        values=[v for t,v in parts if t==tag]
        if len(values)==1 and len(values[0])==4:
            key=slots.decode(struct.unpack("<I",values[0])[0])
            if key:result[name]=(key.origin,key.local)
    for name,tag in TEXTURES.items():
        hits=[v for t,v in parts if t==tag]
        if len(hits)==1 and hits[0].endswith(b"\0") and b"\0" not in hits[0][:-1] and hits[0][:-1]:result[name]=hits[0][:-1].decode("cp1252")
    return result

def normalize(values,index):
    result={}
    for name,value in values.items():
        if name in LINKS:
            if value is None:result[name]=None;continue
            if not isinstance(value,(tuple,list)) or len(value)!=2:raise ValueError("Use plugin and local FormID for "+name)
            key=Identity(*value)
            row=index.active.get(key)
            if not row or row["signature"]!=LINKS[name][1]:raise ValueError("Wrong or missing record for "+name)
            result[name]=(key.origin,key.local)
        elif name in TEXTURES:
            if value is None or value=="":result[name]=None;continue
            if not isinstance(value,str):raise ValueError("Expected texture path")
            pieces=value.replace("\\","/").split("/")
            if any(not p or p in (".","..") or ":" in p or "\0" in p for p in pieces) or not pieces[-1].casefold().endswith(".dds") or len(value.encode("cp1252"))>255:
                raise ValueError("Unsafe relative DDS path")
            result[name]=value
        elif name in FIELDS:
            _,fmt=FIELDS[name]
            if not isinstance(value,(tuple,list)) or any(type(v) not in (int,float) or not isfinite(v) for v in value):
                raise ValueError("Invalid "+name)
            try:parsed=struct.unpack(fmt,struct.pack(fmt,*value))
            except (struct.error,OverflowError) as exc:raise ValueError("Invalid "+name) from exc
            if not all(isfinite(v) for v in parsed):raise ValueError("Invalid "+name)
            if name in ("heights","lod_height","map_offset") and any(abs(v)>1e7 for v in parsed):raise ValueError("World value out of range")
            if name=="inheritance" and parsed[0]&~0x3f:raise ValueError("Unknown parent flags")
            if name=="map_offset" and parsed[0]<=0:raise ValueError("Map scale must be positive")
            if name=="map_size_bounds" and (min(parsed[:2])<=0 or parsed[2]>parsed[4] or parsed[3]<parsed[5]):
                raise ValueError("Map size/bounds invalid")
            result[name]=parsed
        else:raise ValueError("Unsupported environment field "+name)
    return result

def apply(parts,values,slots):
    parts=list(parts)
    for name,value in values.items():
        if name in LINKS:
            tag=LINKS[name][0]
            raw=None if value is None else struct.pack("<I",slots.encode(Identity(*value)))
        elif name in TEXTURES:
            tag=TEXTURES[name];raw=None if value is None else value.encode("cp1252")+b"\0"
        else:
            tag,fmt=FIELDS[name];raw=struct.pack(fmt,*value)
        hits=[i for i,(t,_) in enumerate(parts) if t==tag]
        if len(hits)>1:raise ValueError("Ambiguous world field "+name)
        if hits:
            if raw is None:parts.pop(hits[0])
            else:
                if name not in TEXTURES and len(parts[hits[0]][1])!=len(raw):raise ValueError("Unsupported existing layout "+name)
                parts[hits[0]]=(tag,raw)
        elif raw is not None:
            rank=ORDER.index(tag)
            pos=next((i for i,(t,_) in enumerate(parts) if t in ORDER and ORDER.index(t)>rank),len(parts))
            parts.insert(pos,(tag,raw))
    return parts

def validate_parent(index,key,environment):
    """Reject missing parents and cycles before any draft mutation."""
    mask=environment.get("inheritance",(0,))[0]
    parent=environment.get("parent")
    if mask and not parent:raise ValueError("Inheritance requires a parent worldspace")
    seen={key}
    while parent:
        parent_key=Identity(*parent)
        if parent_key in seen:raise ValueError("Worldspace inheritance cycle")
        seen.add(parent_key)
        row=index.worlds.get(parent_key)
        if row is None:raise ValueError("Missing parent worldspace")
        parent=row.get("environment",{}).get("parent")

def effective(index,key):
    """Resolve each inherited property with provenance; unresolved data stays absent."""
    values={};providers={};issues=[]
    def field(k,name,seen):
        if k in seen or k not in index.worlds:
            issues.append("Invalid inheritance chain for "+name);return None,None
        env=index.worlds[k].get("environment",{})
        parent=env.get("parent")
        if parent and env.get("inheritance",(0,))[0]&INHERIT.get(name,0):
            return field(Identity(*parent),name,seen|{k})
        return env.get(name),k
    for name in set(FIELDS)|set(LINKS)|set(TEXTURES):
        value,provider=field(key,name,set())
        if value is not None:
            values[name]=value;providers[name]=(provider.origin,provider.local)
    return {"values":values,"providers":providers,"issues":issues}
