"""Independent classic TES3 format implementation.
Layout reference: OpenMW/openmw components/esm3/aipackage.cpp and .hpp.
"""
import struct
import math

FORMATS={
 b"AI_W":("<hhB8BB",("distance","duration","time_of_day",*("idle"+str(i) for i in range(1,9)),"repeat")),
 b"AI_T":("<fffB3s",("x","y","z","repeat","padding")),
 b"AI_F":("<fffh32sB1s",("x","y","z","duration","target","repeat","padding")),
 b"AI_E":("<fffh32sB1s",("x","y","z","duration","target","repeat","padding")),
 b"AI_A":("<32sB",("target","repeat")),
}

def decode(tag,raw):
    if tag not in FORMATS:raise ValueError("Unknown AI package")
    fmt,keys=FORMATS[tag]
    if len(raw)!=struct.calcsize(fmt):raise ValueError("Invalid AI package length")
    values=dict(zip(keys,struct.unpack(fmt,raw)))
    if "target" in values:values["target"]=values["target"].split(b"\0",1)[0].decode("cp1252")
    if any(isinstance(v,float) and not math.isfinite(v) for v in values.values()):raise ValueError("Nonfinite destination")
    values.pop("padding",None)
    return values

def edit(tag,raw,**changes):
    values=decode(tag,raw)
    if set(changes)-set(values):raise ValueError("Unknown AI property")
    fmt,keys=FORMATS[tag]
    original=dict(zip(keys,struct.unpack(fmt,raw)))
    for k,v in changes.items():
        if k=="target":
            if not isinstance(v,str) or not v.strip() or "\0" in v:raise ValueError("Invalid target")
            v=v.encode("cp1252")
            if len(v)>31:raise ValueError("Target too long")
        elif k in ("x","y","z"):
            if type(v) not in (int,float) or not math.isfinite(v):raise ValueError("Invalid destination")
        elif k=="repeat":
            if type(v) not in (bool,int) or v not in (0,1):raise ValueError("Invalid repeat")
        elif type(v)!=int or v<0 or (k.startswith("idle") and v>100) or (k=="time_of_day" and v>23):
            raise ValueError("Invalid AI property")
        original[k]=v
    try:return struct.pack(fmt,*(original[k] for k in keys))
    except (struct.error,OverflowError) as e:raise ValueError("AI property outside native range") from e

def create(tag,**changes):
    if tag not in FORMATS:raise ValueError("Unknown AI package")
    if tag in (b"AI_F",b"AI_E",b"AI_A") and "target" not in changes:raise ValueError("Target required")
    return edit(tag,bytes(struct.calcsize(FORMATS[tag][0])),**changes)

def inspect(parts):
    packages=[]
    previous=None
    for index,(tag,raw) in enumerate(parts):
        if tag in FORMATS:
            previous={"tag":tag,"index":index,"properties":decode(tag,raw)}
            packages.append(previous)
        elif tag==b"CNDT":
            if previous is None or previous["tag"] not in (b"AI_F",b"AI_E") or "cell" in previous:raise ValueError("Orphan or duplicate package cell")
            previous["cell"]=raw.rstrip(b"\0").decode("cp1252")
            previous["cell_index"]=index
        else:previous=None
    return packages

def encode_package(tag,properties,cell=None):
    parts=[(tag,create(tag,**properties))]
    if cell is not None:
        if tag not in (b"AI_F",b"AI_E") or not isinstance(cell,str) or not cell.strip() or "\0" in cell:raise ValueError("Invalid package cell")
        parts.append((b"CNDT",cell.encode("cp1252")+b"\0"))
    return parts

def manage(data,index,action,revision,*,package=None,destination=None,tag=None,properties=None,cell=None):
    """Atomic package-list edit; indices refer to package order, not subrecords."""
    import hashlib
    from .native_parser import parse,subrecords
    from .native_payload_edit import insert_adjacent,remove
    if hashlib.sha256(data).hexdigest()!=revision:raise ValueError("Stale revision")
    nodes=parse("morrowind",data)
    if type(index)!=int or not 0<=index<len(nodes) or nodes[index].signature not in (b"NPC_",b"CREA"):raise ValueError("Expected actor")
    parts=list(subrecords("morrowind",nodes[index]))
    if any(k==b"DELE" for k,v in parts):raise ValueError("Deleted actor")
    rows=inspect(parts)
    blocks=[parts[r["index"]:r.get("cell_index",r["index"])+1] for r in rows]
    if action=="add":
        block=encode_package(tag,properties or {},cell)
        destination=len(blocks) if destination is None else destination
        if type(destination)!=int or not 0<=destination<=len(blocks):raise ValueError("Invalid destination")
        blocks.insert(destination,block)
    elif action in ("remove","move"):
        if type(package)!=int or not 0<=package<len(blocks):raise ValueError("Invalid package")
        block=blocks.pop(package)
        if action=="move":
            if type(destination)!=int or not 0<=destination<=len(blocks):raise ValueError("Invalid destination")
            blocks.insert(destination,block)
    else:raise ValueError("Unknown package action")
    # Refuse interleaved package blocks rather than moving unrelated fields.
    indices=[i for r in rows for i in range(r["index"],r.get("cell_index",r["index"])+1)]
    if indices and indices!=list(range(indices[0],indices[-1]+1)):raise ValueError("Noncontiguous package list")
    candidate=data
    def rev():return hashlib.sha256(candidate).hexdigest()
    start=indices[0] if indices else len(parts)
    for i in reversed(indices):
        k,v=parts[i];occ=sum(t==k for t,_ in parts[:i])
        candidate=remove("morrowind",candidate,(index,),k,occ,v,rev())
    remaining=[p for i,p in enumerate(parts) if i not in set(indices)]
    if not remaining:raise ValueError("No actor anchor")
    anchor=min(start,len(remaining)-1)
    after=start>=len(remaining)
    for k,v in [p for block in blocks for p in block]:
        ak,av=remaining[anchor];occ=sum(t==ak for t,_ in remaining[:anchor])
        candidate=insert_adjacent("morrowind",candidate,(index,),ak,occ,av,k,v,rev(),after=after)
        pos=anchor+int(after);remaining.insert(pos,(k,v));anchor=pos;after=True
    inspect(list(subrecords("morrowind",parse("morrowind",candidate)[index])))
    return candidate
