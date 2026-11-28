"""Read-only world hierarchy and spatial metadata."""
import struct
from .native_profiles import PROFILES
from .native_parser import parse, subrecords
from .native_catalog import inspect_node
from .historical_schema import group_label

def world_records(profile, data, slots=None):
    if PROFILES[profile].family=="TES3":
        raise ValueError("TES3 cell hierarchy requires separate decoder")
    def walk(nodes, ancestry):
        for node in nodes:
            if node.signature==b"GRUP":
                kind=struct.unpack_from("<i",node.header,12)[0]
                label=node.header[8:12]
                role,value=group_label(kind,label,slots)
                yield from walk(node.children,ancestry+((kind,role,value),))
            elif node.signature in (b"WRLD",b"CELL",b"LAND",b"REFR",b"ACHR",b"ACRE"):
                row=inspect_node(profile,node,slots)
                row["signature"]=node.signature.decode("ascii")
                row["ancestry"]=ancestry
                row["spatial"]=spatial(row["signature"],row["parts"])
                row["world"]=next((owner for _,role,owner in reversed(ancestry) if role=="world"),None)
                row["cell"]=next((owner for _,role,owner in reversed(ancestry) if role=="cell"),None)
                row["bucket"]=next((kind for kind,_,_ in reversed(ancestry) if kind in (8,9,10)),None)
                row["persistent"]=bool(struct.unpack_from("<I",node.header,8)[0]&0x400)
                yield row
    if slots is None:
        raise ValueError("plugin-relative slots required")
    yield from walk(parse(profile,data),())

def spatial(signature, parts):
    result={}
    for tag,raw in parts:
        if signature in ("REFR","ACHR","ACRE") and tag==b"DATA" and len(raw)==24:
            values=struct.unpack("<6f",raw)
            result["position"]=values[:3]
            result["rotation"]=values[3:]
        elif signature in ("REFR","ACHR","ACRE") and tag==b"XSCL" and len(raw)==4:
            result["scale"]=struct.unpack("<f",raw)[0]
        elif signature=="REFR" and tag==b"XTEL" and len(raw)==32:
            target,*values=struct.unpack("<I6fI",raw)
            result["teleport"]={"raw_target":target,"arrival":values[:3],"rotation":values[3:6],"flags":values[6]}
        elif signature=="REFR" and tag==b"XLKR" and len(raw)==4:
            result["linked_reference"]=struct.unpack("<I",raw)[0]
        elif signature=="CELL" and tag==b"XCLC" and len(raw) in (8,12):
            result["grid"]=struct.unpack_from("<2i",raw)
    if signature=="REFR" and any(tag in (b"XPRM",b"XPOD",b"XPTL",b"XRMR",b"XLRM",b"XNDP") for tag,_ in parts):
        from .fnv_portal_fields import inspect
        try:result["native_markers"]=inspect(parts)[0]
        except ValueError as exc:result["native_marker_warning"]=str(exc)
    return result
