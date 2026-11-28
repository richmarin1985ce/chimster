"""Read-only item catalog. Unknown layouts remain opaque, never guessed."""
import struct
from math import isfinite
from .native_parser import parse,subrecords
from .native_profiles import PROFILES

ITEMS={b"BOOK",b"NOTE",b"WEAP",b"ARMO",b"CLOT",b"ALCH",b"INGR",b"AMMO",b"MISC",b"KEYM",b"CONT",b"LVLI"}
LOCALIZED={ "skyrim","skyrim-se","fallout4" }

def inspect(profile,data):
    if profile not in PROFILES or PROFILES[profile].family=="TES3":raise ValueError("Unsupported item catalog profile")
    nodes=parse(profile,data)
    if not nodes or nodes[0].signature!=b"TES4":raise ValueError("Missing plugin header")
    localized=profile in LOCALIZED and bool(struct.unpack_from("<I",nodes[0].header,8)[0]&0x80)
    rows=[]
    def walk(nodes):
        for node in nodes:
            if node.signature==b"GRUP":walk(node.children);continue
            if node.signature not in ITEMS:continue
            flags,fid=struct.unpack_from("<II",node.header,8)
            if flags&0x20:continue
            row={"signature":node.signature.decode(),"form_id_raw":fid,"fields":{},"issues":[],"raw":[]}
            for tag,v in subrecords(profile,node):
                k=tag.decode("ascii");row["raw"].append((k,v.hex()))
                if tag in (b"EDID",b"FULL",b"DESC",b"MODL",b"ICON",b"TNAM") and (tag!=b"TNAM" or node.signature==b"NOTE" and profile=="new-vegas"):
                    if localized and tag in (b"FULL",b"DESC"):
                        value={"string_id":struct.unpack("<I",v)[0]} if len(v)==4 else {"opaque":v.hex()}
                    elif v.endswith(b"\0") and b"\0" not in v[:-1]:
                        value={"text":v[:-1].decode("cp1252",errors="replace")}
                    else:value={"opaque":v.hex()}
                    row["fields"].setdefault(k,[]).append(value)
                if tag==b"DATA" and node.signature==b"BOOK" and profile in ("fallout3","new-vegas") and len(v)==10:
                    f,s,val,w=struct.unpack("<Bbif",v)
                    if isfinite(w):row["book_data"]={"flags":f,"skill_raw":s,"value":val,"weight":w}
                    else:row["issues"].append("Nonfinite book weight")
            rows.append(row)
    walk(nodes)
    return {"profile":profile,"localized":localized,"items":rows}
