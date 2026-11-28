"""Experimental FNV WTHR authoring; documented fields only, no engine validation."""
import struct
from math import isfinite
from .record_graph import Identity
from .fnv_world import cstr
from .fnv_patch import record,sub

CLOUD_TAGS=(b"DNAM",b"CNAM",b"ANAM",b"BNAM")
def bytes_field(values,n):
    if len(values)!=n or any(type(v)!=int or not 0<=v<=255 for v in values):raise ValueError("Expected "+str(n)+" byte values")
    return tuple(values)
def texture(path):
    if not isinstance(path,str):raise ValueError("Expected texture path")
    if path:
        parts=path.replace("\\","/").split("/")
        if any(not p or p in (".","..") or ":" in p or "\0" in p for p in parts) or not parts[-1].lower().endswith(".dds") or len(path.encode("cp1252"))>255:raise ValueError("Unsafe texture path")
    return path

def defaults():
    # Explicit starter preset, not a clone of an official weather.
    return {"cloud_textures":[""]*4,"cloud_speed":[0]*4,"cloud_colors":[255]*96,
            "colors":[v for color in [(105,150,195,255),(150,170,185,255),(0,0,0,255),(110,115,120,255),(255,240,210,255),(255,235,180,255),(80,80,100,255),(170,190,205,255),(170,180,190,255),(0,0,0,255)] for _ in range(6) for v in color],
            "fog":[0,50000,0,30000,1,1],"data":[20,0,0,20,128,0,0,255,0,255,0,1,255,255,255],"sounds":[],"image_modifiers":[None]*6}

def validate(spec,index):
    base=defaults()
    if set(spec)-set(base):raise ValueError("Unknown weather fields")
    base.update(spec)
    clouds=tuple(texture(p) for p in base["cloud_textures"])
    if len(clouds)!=4:raise ValueError("Four cloud texture slots required")
    fog=tuple(struct.unpack("<6f",struct.pack("<6f",*base["fog"])))
    if not all(isfinite(v) and 0<=v<=1e7 for v in fog) or fog[0]>fog[1] or fog[2]>fog[3]:raise ValueError("Invalid fog distances or power")
    data=bytes_field(base["data"],15)
    if data[11] not in (0,1,2,4,8):raise ValueError("Invalid weather classification")
    def linked(value,signature):
        if value is None:return None
        key=Identity(*value)
        if index.active.get(key,{}).get("signature")!=signature:raise ValueError("Invalid "+signature+" link")
        return (key.origin,key.local)
    mods=tuple(linked(v,"IMAD") for v in base["image_modifiers"])
    if len(mods)!=6:raise ValueError("Six image modifiers required")
    sounds=[]
    for key,kind in base["sounds"]:
        if type(kind)!=int or kind not in (0,1,2,3) or key is None:raise ValueError("Invalid weather sound")
        sounds.append((linked(key,"SOUN"),kind))
    if len(sounds)>64:raise ValueError("Sound limit")
    return {"cloud_textures":clouds,"cloud_speed":bytes_field(base["cloud_speed"],4),"cloud_colors":bytes_field(base["cloud_colors"],96),
            "colors":bytes_field(base["colors"],240),"fog":fog,"data":data,"sounds":sounds,"image_modifiers":mods}

def encode(row,slots):
    spec=row["weather_spec"]
    def fid(key):return struct.pack("<I",slots.encode(Identity(*key)))
    parts=[(b"EDID",cstr(row["editor_id"]))]
    for i,key in enumerate(spec["image_modifiers"]):
        if key:parts.append((bytes([i])+b"IAD",fid(key)))
    parts.extend((tag,cstr(path)) for tag,path in zip(CLOUD_TAGS,spec["cloud_textures"]))
    parts.extend([(b"LNAM",bytes(4)),(b"ONAM",bytes(spec["cloud_speed"])),(b"PNAM",bytes(spec["cloud_colors"])),
                  (b"NAM0",bytes(spec["colors"])),(b"FNAM",struct.pack("<6f",*spec["fog"])),(b"INAM",bytes(304)),(b"DATA",bytes(spec["data"]))])
    parts.extend((b"SNAM",fid(key)+struct.pack("<I",kind)) for key,kind in spec["sounds"])
    return record(b"WTHR",b"".join(sub(t,v) for t,v in parts),slots.encode(row["key"]))

def decode(parts,slots):
    parts=list(parts);fields=dict(parts)
    lengths={b"ONAM":4,b"PNAM":96,b"NAM0":240,b"FNAM":24,b"DATA":15}
    if any(len(fields.get(t,b""))!=n for t,n in lengths.items()):return None
    def key(raw):
        if len(raw)!=4:return None
        k=slots.decode(struct.unpack("<I",raw)[0]);return (k.origin,k.local) if k else None
    return {"cloud_textures":tuple(fields.get(t,b"").rstrip(b"\0").decode("cp1252") for t in CLOUD_TAGS),
        "cloud_speed":tuple(fields[b"ONAM"]),"cloud_colors":tuple(fields[b"PNAM"]),"colors":tuple(fields[b"NAM0"]),
        "fog":struct.unpack("<6f",fields[b"FNAM"]),"data":tuple(fields[b"DATA"]),
        "sounds":[(key(v[:4]),struct.unpack_from("<I",v,4)[0]) for t,v in parts if t==b"SNAM" and len(v)==8],
        "image_modifiers":tuple(key(fields.get(bytes([i])+b"IAD",b"")) for i in range(6))}
