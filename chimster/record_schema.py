"""Explicit typed field schemas for selected FNV records, not arbitrary binary editing."""
import math,struct
from .fnv_records import text
from .fnv_content import asset
from .fnv_world import cstr
TEXT={"WRLD":{"FULL"},"CELL":{"FULL"},"BOOK":{"FULL","DESC","MODL"},"NOTE":{"FULL"},"STAT":{"MODL"},"MISC":{"FULL","MODL"},"FACT":{"FULL"},"QUST":{"FULL"},"DIAL":{"FULL"},"NPC_":{"FULL"},"RACE":{"FULL","DESC"},"WEAP":{"FULL"},"ARMO":{"FULL"},"REPU":{"FULL"},"CONT":{"FULL","MODL"},"AMMO":{"FULL","MODL","ONAM","QNAM"},"KEYM":{"FULL","MODL"},"ALCH":{"FULL","MODL"},"CLAS":{"FULL","DESC"},"MGEF":{"FULL","DESC"},"SPEL":{"FULL"},"PERK":{"FULL","DESC"}}
def codec(sig,tag,edid,parts):
    if tag in TEXT.get(sig,set()):return "model" if tag=="MODL" else "text"
    if sig=="GLOB" and tag=="FLTV":
        types=[v for k,v in parts if k==b"FNAM"]
        if len(types)!=1 or types[0] not in (b"s",b"l",b"f"):raise ValueError("unknown global type")
        return {b"s":"short_global",b"l":"long_global",b"f":"float"}[types[0]]
    if sig=="GMST" and tag=="DATA" and edid:return {"s":"text","f":"float","i":"int"}.get(edid[0])
    if sig in {"MISC","KEYM"} and tag=="DATA":return "item"
    if sig=="REPU" and tag=="DATA":return "positive_float"
    if sig in {"LVLI","LVLN"} and tag=="LVLD":return "percentage_byte"
    if sig=="WEAP" and tag=="DATA":return "weapon"
    if sig=="ARMO" and tag=="DATA":return "armor"
    if sig=="ALCH" and tag=="DATA":return "weight"
    if sig=="NPC_" and tag=="DATA":return "npc_stats"
    if sig=="BOOK" and tag=="DATA":return "book"
    if sig in {"STAT","MISC","BOOK","WEAP","ARMO","CONT","AMMO","KEYM","ALCH","NPC_","LVLI","LVLN"} and tag=="OBND":return "bounds"
    if sig=="REFR" and tag=="XSCL":return "scale"
    if sig=="REFR" and tag=="DATA":return "transform"
    if sig=="STAT" and tag=="BRUS":return "brush"
    return None
def integer(x,lo,hi):
    if type(x) is not int or not lo<=x<=hi:raise ValueError("integer outside field bounds")
    return x
def number(x,lo=-3.4e38,hi=3.4e38):
    if type(x) not in (int,float) or not math.isfinite(x) or not lo<=x<=hi:raise ValueError("number outside field bounds")
    return x
def sequence(v,n):
    if not isinstance(v,(list,tuple)) or len(v)!=n:raise ValueError("wrong field dimension")
    return v
def encode(kind,value):
    if kind=="text":return cstr(value)
    if kind=="model":return asset(value,".nif")
    if kind=="int":return struct.pack("<i",integer(value,-2**31,2**31-1))
    if kind in ("float","scale","short_global","long_global"):
        v=number(value,0.01,10) if kind=="scale" else integer(value,-32768,32767) if kind=="short_global" else integer(value,-16777216,16777216) if kind=="long_global" else number(value)
        return struct.pack("<f",v)
    if kind=="percentage_byte":return bytes([integer(value,0,100)])
    if kind in ("positive_float","weight"):return struct.pack("<f",number(value,0,1000 if kind=="weight" else 1e6))
    if kind in ("armor","weapon"):
        keys={"value","health","weight"}|({"damage","clip_size"} if kind=="weapon" else set())
        if not isinstance(value,dict) or set(value)!=keys:raise ValueError("invalid equipment fields")
        raw=struct.pack("<iif",integer(value["value"],0,2**31-1),integer(value["health"],1,2**31-1),number(value["weight"],0,1000))
        return raw+(struct.pack("<hB",integer(value["damage"],0,32767),integer(value["clip_size"],0,255)) if kind=="weapon" else b"")
    if kind=="npc_stats":
        if not isinstance(value,dict) or set(value)!={"health","special"}:raise ValueError("invalid NPC stats")
        return struct.pack("<i7B",integer(value["health"],1,2**31-1),*[integer(v,1,10) for v in sequence(value["special"],7)])
    if kind=="brush":return struct.pack("<b",integer(value,-1,9))
    if kind=="bounds":
        v=[integer(x,-32768,32767) for x in sequence(value,6)]
        if any(v[i]>v[i+3] for i in range(3)):raise ValueError("inverted bounds")
        return struct.pack("<6h",*v)
    if kind=="transform":return struct.pack("<6f",*[number(x,-1e7,1e7) for x in sequence(value,6)])
    if kind in ("item","book"):
        keys={"value","weight"}|({"flags","skill"} if kind=="book" else set())
        if not isinstance(value,dict) or set(value)!=keys:raise ValueError("invalid item fields")
        tail=struct.pack("<if",integer(value["value"],0,2**31-1),number(value["weight"],0,1000))
        if kind=="item":return tail
        skill=integer(value["skill"],-1,13)
        if skill==1:raise ValueError("unknown skill")
        return struct.pack("<Bb",integer(value["flags"],0,3),skill)+tail
    raise ValueError("field not writable")
def decode(kind,raw):
    if kind in ("text","model"):return text(raw)
    if kind=="int":return struct.unpack("<i",raw)[0]
    if kind in ("float","scale","short_global","long_global"):
        v=struct.unpack("<f",raw)[0]
        if not math.isfinite(v):raise ValueError("nonfinite field")
        return int(v) if kind.endswith("_global") and v.is_integer() else v
    if kind=="percentage_byte":return struct.unpack("<B",raw)[0]
    if kind in ("positive_float","weight"):
        v=struct.unpack("<f",raw)[0]
        if not math.isfinite(v):raise ValueError("nonfinite field")
        return v
    if kind=="armor":return dict(zip(("value","health","weight"),struct.unpack("<iif",raw)))
    if kind=="weapon":return dict(zip(("value","health","weight","damage","clip_size"),struct.unpack("<iifhB",raw)))
    if kind=="npc_stats":
        health,*special=struct.unpack("<i7B",raw);return {"health":health,"special":special}
    if kind=="brush":return struct.unpack("<b",raw)[0]
    if kind=="bounds":return list(struct.unpack("<6h",raw))
    if kind=="transform":return list(struct.unpack("<6f",raw))
    if kind=="item":return dict(zip(("value","weight"),struct.unpack("<if",raw)))
    if kind=="book":return dict(zip(("flags","skill","value","weight"),struct.unpack("<Bbif",raw)))
    raise ValueError("unknown codec")
def fields(sig,edid,parts):
    parts=list(parts);result=[]
    from .record_graph import FIELDS
    from collections import Counter
    counts=Counter(k for k,v in parts)
    for k,v in parts:
        tag=k.decode("ascii",errors="replace");entry={"tag":tag,"bytes":len(v),"hex_preview":v[:64].hex(),"writable":False}
        try:
            kind=codec(sig,tag,edid,parts)
            if kind:
                value=decode(kind,v);entry.update(type=kind,value=value,writable=counts[k]==1)
        except (ValueError,struct.error,UnicodeError):entry["warning"]="unsupported field layout"
        ref=FIELDS.get((sig,k))
        if ref and len(v)==ref[0]:
            entry["reference"]={"raw_formid":struct.unpack_from("<I",v,ref[1])[0],"expected_types":sorted(ref[2]) if ref[2] else None}
        result.append(entry)
    return result
