"""Bounded FNV CLMT authoring with explicit existing weather records."""
import struct
from .record_graph import Identity
from .fnv_patch import sub,record
from .fnv_world import cstr

def validate(spec,index):
    weather=spec.get("weather",[])
    if not isinstance(weather,(tuple,list)) or not 1<=len(weather)<=64:raise ValueError("Choose 1–64 weather records")
    entries=[];seen=set()
    for row in weather:
        if len(row)!=3:raise ValueError("Weather entry requires identity, chance, optional global")
        key,chance,glob=row
        key=Identity(*key)
        if key in seen or index.active.get(key,{}).get("signature")!="WTHR":raise ValueError("Invalid or duplicate weather")
        if type(chance)!=int or not 0<=chance<=100:raise ValueError("Weather chance must be 0–100")
        seen.add(key)
        if glob is not None:
            g=Identity(*glob)
            if index.active.get(g,{}).get("signature")!="GLOB":raise ValueError("Invalid global chance modifier")
            glob=(g.origin,g.local)
        entries.append(((key.origin,key.local),chance,glob))
    if sum(r[1] for r in entries)!=100:raise ValueError("Base weather chances must total 100")
    timing=tuple(spec.get("timing",(36,48,108,120,0,0)))
    if len(timing)!=6 or any(type(v)!=int or not 0<=v<=255 for v in timing) or not 0<=timing[0]<=timing[1]<=timing[2]<=timing[3]<=144:
        raise ValueError("Invalid climate timing bytes (sunrise/sunset in ten-minute increments)")
    result={"weather":entries,"timing":timing}
    for name in ("sun","glare"):
        value=spec.get(name,"")
        if not isinstance(value,str):raise ValueError("Expected texture string")
        if value:
            parts=value.replace("\\","/").split("/")
            if any(not p or p in (".","..") or ":" in p or "\0" in p for p in parts) or not parts[-1].casefold().endswith(".dds") or len(value.encode("cp1252"))>255:
                raise ValueError("Unsafe climate texture path")
        result[name]=value
    return result

def encode(row,slots):
    spec=row["climate_spec"]
    weather=b"".join(struct.pack("<IiI",slots.encode(Identity(*key)),chance,slots.encode(Identity(*glob)) if glob else 0) for key,chance,glob in spec["weather"])
    fields=[(b"EDID",cstr(row["editor_id"])),(b"WLST",weather)]
    if spec["sun"]:fields.append((b"FNAM",cstr(spec["sun"])))
    if spec["glare"]:fields.append((b"GNAM",cstr(spec["glare"])))
    fields.append((b"TNAM",bytes(spec["timing"])))
    return record(b"CLMT",b"".join(sub(t,v) for t,v in fields),slots.encode(row["key"]))

def decode(parts,slots):
    fields=dict(parts)
    raw=fields.get(b"WLST",b"")
    timing=fields.get(b"TNAM",b"")
    if len(raw)%12 or len(timing)!=6:return None
    entries=[]
    for weather,chance,glob in struct.iter_unpack("<IiI",raw):
        key=slots.decode(weather);g=slots.decode(glob)
        if key is None:return None
        entries.append(((key.origin,key.local),chance,(g.origin,g.local) if g else None))
    return {"weather":entries,"timing":tuple(timing),
            "sun":fields.get(b"FNAM",b"").rstrip(b"\0").decode("cp1252",errors="replace"),
            "glare":fields.get(b"GNAM",b"").rstrip(b"\0").decode("cp1252",errors="replace")}
