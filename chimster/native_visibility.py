"""Read-only visibility metadata; raw fields retained, no inferred native geometry."""
import struct
from .native_parser import parse,subrecords
FIELDS={b"XOCP",b"XPLT",b"XRMR",b"XLRM",b"XPRM",b"XPOD",b"XPTL",b"XORD",b"XMBR",b"XMBO",b"XMBP",b"XRMK"}
PROFILES={"fallout3","new-vegas","skyrim","skyrim-se","fallout4"}
def inspect(profile,data):
    profile={"newvegas":"new-vegas","skyrimse":"skyrim-se"}.get(profile,profile)
    if profile not in PROFILES:raise ValueError("Visibility profile not supported")
    result=[]
    def walk(nodes,groups=()):
        for node in nodes:
            if node.signature==b"GRUP":
                walk(node.children,groups+((node.header[8:12].hex(),struct.unpack_from("<i",node.header,12)[0]),))
            elif node.signature==b"REFR":
                fields=list(subrecords(profile,node))
                found=[(k.decode(),v.hex()) for k,v in fields if k in FIELDS]
                if not found:continue
                flags,form=struct.unpack_from("<II",node.header,8)
                result.append({"form_id_raw":form,"flags":flags,"groups":groups,"visibility_fields":found,
                    "transform_fields":[v.hex() for k,v in fields if k==b"DATA"],
                    "base_fields":[v.hex() for k,v in fields if k==b"NAME"],
                    "status":"candidate metadata; geometry and master-relative links not decoded"})
    walk(parse(profile,data))
    return result

def resolve_classic(profile,data,plugin):
    """Resolve classic file-local identities and common REFR transforms.
    Visibility-specific fields remain opaque until their schema is verified.
    """
    from math import isfinite
    from .record_graph import Slots
    profile={"newvegas":"new-vegas"}.get(profile,profile)
    if profile not in {"fallout3","new-vegas","skyrim"}:
        raise ValueError("Classic full-slot profiles only")
    nodes=parse(profile,data)
    if not nodes or nodes[0].signature!=b"TES4":raise ValueError("Missing TES4 header")
    masters=[]
    for tag,raw in subrecords(profile,nodes[0]):
        if tag==b"MAST":
            if not raw.endswith(b"\0") or b"\0" in raw[:-1]:raise ValueError("Invalid master name")
            masters.append(raw[:-1].decode("cp1252"))
    slots=Slots(plugin,masters)
    def identity(raw):
        v=slots.decode(raw)
        return None if v is None else {"origin":v.origin,"local":v.local}
    rows=inspect(profile,data);seen=set()
    for row in rows:
        raw=row["form_id_raw"]
        if raw in seen:raise ValueError("Duplicate visibility reference")
        seen.add(raw)
        row["identity"]=identity(raw)
        row["deleted"]=bool(row["flags"]&0x20)
        base=row["base_fields"];transform=row["transform_fields"]
        row["base_identity"]=identity(struct.unpack("<I",bytes.fromhex(base[0]))[0]) if len(base)==1 and len(base[0])==8 else None
        if len(transform)==1 and len(transform[0])==48:
            values=struct.unpack("<6f",bytes.fromhex(transform[0]))
            if all(isfinite(v) for v in values):
                row["position_game_units"]=values[:3]
                row["rotation_radians"]=values[3:]
        row["status"]="classic identity and common transform inspection; visibility geometry opaque"
    return rows

def decode_geometry(profile,row):
    """Decode documented fields without assuming quaternion order or coordinate basis."""
    from math import isfinite
    profile={"newvegas":"new-vegas","skyrimse":"skyrim-se"}.get(profile,profile)
    if profile not in {"fallout3","new-vegas","skyrim","skyrim-se"}:raise ValueError("Unsupported geometry schema")
    fields={}
    for k,v in row["visibility_fields"]:fields.setdefault(k,[]).append(bytes.fromhex(v))
    out={"issues":[],"raw":row,"geometry":{}}
    g=out["geometry"]
    def one(tag,fmt):
        values=fields.get(tag,[])
        if not values:return None
        if len(values)!=1 or len(values[0])!=struct.calcsize(fmt):
            out["issues"].append(tag+": unexpected size or repetition");return None
        v=struct.unpack(fmt,values[0])
        if not all(isfinite(x) for x in v if isinstance(x,float)):
            out["issues"].append(tag+": nonfinite values");return None
        return v
    p=one("XPRM","<6f4sI")
    if p:
        g["primitive"]={"bounds":p[:3],"color":p[3:6],"unknown":p[6].hex(),"type":p[7]}
    b=one("XMBO","<3f")
    if b:g["multibound_dimensions"]=b
    for tag,kind in (("XPTL","portal"),("XPLT","portal_legacy"),("XOCP","occluder")):
        v=one(tag,"<9f")
        if v:
            if min(v[:2])<=0:out["issues"].append(tag+": nonpositive dimensions")
            else:g[kind]={"dimensions":v[:2],"position":v[2:5],"quaternion_raw":v[5:9]}
    h=one("XRMR","<H2s" if profile in {"fallout3","new-vegas"} else "<BB2s")
    if h:
        g["room_link_count"]=h[0]
        if len(h)==3:g["room_flags"]=h[1]
        g["room_header_unknown"]=h[-1].hex()
    links=[]
    for v in fields.get("XLRM",[]):
        if len(v)==4:links.append(struct.unpack("<I",v)[0])
        else:out["issues"].append("XLRM: invalid size")
    if links or h:
        g["linked_rooms_raw"]=links
        if h and len(links)!=h[0]:out["issues"].append("XRMR link count mismatch")
    pairs=[]
    for v in fields.get("XPOD",[]):
        if len(v)%8 or not v:out["issues"].append("XPOD: invalid pair array");continue
        pairs.extend(struct.iter_unpack("<II",v))
    if pairs:g["portal_room_pairs_raw"]=pairs
    v=one("XMBR","<I")
    if v:g["multibound_reference_raw"]=v[0]
    v=one("XORD","<4I")
    if v:g["linked_occlusion_raw"]=v
    return out
