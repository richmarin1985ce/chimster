"""Documented FNV room/portal fields. Unknown bytes and quaternion ordering stay explicit."""
import math,struct

TAGS={b"XPRM",b"XTRI",b"XPOD",b"XPTL",b"XRMR",b"XLRM",b"XNDP"}
def inspect(parts):
    """Parse marker fields and return typed offsets without assuming a complete record."""
    result={};edges=[];rooms=[];seen=set()
    for i,(tag,raw) in enumerate(parts):
        if tag not in TAGS:continue
        if tag!=b"XLRM" and tag in seen:raise ValueError("duplicate marker field")
        seen.add(tag)
        if tag==b"XPRM":
            if len(raw)!=32:raise ValueError("invalid XPRM size")
            values=struct.unpack("<6f4sI",raw)
            if not all(math.isfinite(v) for v in values[:6]) or any(v<0 for v in values[:3]) or values[-1] not in (0,1,2,3):
                raise ValueError("invalid primitive")
            result["primitive"]={"bounds":values[:3],"color":values[3:6],"unknown":values[6].hex(),"type":values[7]}
        elif tag==b"XTRI":
            if len(raw)!=4:raise ValueError("invalid collision layer")
            result["collision_layer"]=struct.unpack("<I",raw)[0]
        elif tag==b"XPOD":
            if len(raw)!=8:raise ValueError("only two-room portal arrays supported")
            pair=struct.unpack("<2I",raw)
            if not all(pair) or pair[0]==pair[1]:raise ValueError("invalid portal endpoints")
            result["portal_rooms"]=pair
            edges.extend((i,offset,("REFR",)) for offset in (0,4))
        elif tag==b"XPTL":
            if len(raw)!=36:raise ValueError("invalid portal geometry size")
            values=struct.unpack("<9f",raw)
            if not all(math.isfinite(v) for v in values) or min(values[:2])<=0 or math.hypot(*values[5:])<1e-12:
                raise ValueError("invalid portal geometry")
            result["portal_geometry"]={"dimensions":values[:2],"position":values[2:5],"quaternion_raw":values[5:]}
        elif tag==b"XRMR":
            if len(raw)!=4:raise ValueError("invalid room header")
            count,unknown=struct.unpack("<H2s",raw)
            result["room_header"]={"count":count,"unknown":unknown.hex()}
        elif tag==b"XLRM":
            if len(raw)!=4:raise ValueError("invalid linked room")
            target=struct.unpack("<I",raw)[0]
            if not target or target in rooms:raise ValueError("null or duplicate linked room")
            rooms.append(target);edges.append((i,0,("REFR",)))
        elif tag==b"XNDP":
            if len(raw)!=8:raise ValueError("invalid navigation door link")
            target,triangle,tail=struct.unpack("<Ih2s",raw)
            if not target:raise ValueError("null navigation mesh link")
            result["navigation_door"]={"raw_target":target,"triangle":triangle,"tail_hex":tail.hex(),"unknown":raw[4:].hex()}
            edges.append((i,0,("NAVM",)))
    if b"XRMR" in seen:
        if result["room_header"]["count"]!=len(rooms):raise ValueError("room link count mismatch")
        result["linked_rooms"]=tuple(rooms)
    elif rooms:raise ValueError("linked rooms without header")
    if (b"XPOD" in seen)!=(b"XPTL" in seen):raise ValueError("incomplete portal geometry or endpoints")
    if b"XRMR" in seen and b"XPOD" in seen:raise ValueError("mixed room and portal marker")
    return result,edges

def rewrite(parts,remap):
    """Remap only documented marker offsets, preserving all other bytes."""
    parts=list(parts)
    _,edges=inspect(parts)
    changed=0
    for i,offset,kinds in edges:
        tag,raw=parts[i];old=struct.unpack_from("<I",raw,offset)[0]
        new=remap(old,kinds);changed+=old!=new
        parts[i]=(tag,raw[:offset]+struct.pack("<I",new)+raw[offset+4:])
    return parts,changed
