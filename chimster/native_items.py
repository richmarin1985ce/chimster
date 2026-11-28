"""Read-only item catalog. Unknown layouts remain opaque, never guessed."""
import struct
from math import isfinite
from .native_parser import parse,subrecords
from .native_profiles import PROFILES

ITEMS={b"BOOK",b"NOTE",b"WEAP",b"ARMO",b"CLOT",b"ALCH",b"INGR",b"AMMO",b"MISC",b"KEYM",b"CONT",b"LVLI"}
LOCALIZED={ "skyrim","skyrim-se","fallout4" }

def inspect(profile,data):
    if profile not in PROFILES:raise ValueError("Unsupported item catalog profile")
    if PROFILES[profile].family=="TES3":
        from .tes3_items import inspect as tes3_inspect
        return tes3_inspect(profile,data)
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
                if profile=="oblivion" and (node.signature,tag) in OBLIVION_FIELDS:
                    try:row["properties"]=oblivion_properties(node.signature,tag,v)
                    except ValueError as e:row["issues"].append(str(e))
                if tag==b"DATA" and node.signature==b"BOOK" and profile in ("fallout3","new-vegas") and len(v)==10:
                    f,s,val,w=struct.unpack("<Bbif",v)
                    if isfinite(w):row["book_data"]={"flags":f,"skill_raw":s,"value":val,"weight":w}
                    else:row["issues"].append("Nonfinite book weight")
            rows.append(row)
    walk(nodes)
    return {"profile":profile,"localized":localized,"items":rows}

def edit_fallout_book_data(profile,raw,**changes):
    """Typed payload edit, preserving unrelated flag bits and unknown subrecords."""
    if profile not in ("fallout3","new-vegas") or len(raw)!=10:raise ValueError("Unsupported book layout")
    flags,skill,value,weight=struct.unpack("<Bbif",raw)
    if set(changes)-{"skill","value","weight","untakeable"}:raise ValueError("Unknown book property")
    skill=changes.get("skill",skill);value=changes.get("value",value);weight=changes.get("weight",weight)
    if type(skill)!=int or not -128<=skill<=127:raise ValueError("Invalid raw skill")
    if type(value)!=int or not 0<=value<=2147483647:raise ValueError("Invalid value")
    if not isfinite(weight) or not 0<=weight<=1e6:raise ValueError("Invalid weight")
    if "untakeable" in changes:
        if type(changes["untakeable"])!=bool:raise ValueError("Expected boolean")
        flags=(flags&~2)|(2 if changes["untakeable"] else 0)
    return struct.pack("<Bbif",flags,skill,value,weight)

# Classic Oblivion only; no inheritance into the Remastered profile.
OBLIVION_FIELDS={
 (b"WEAP",b"DATA"):("<IffIIIfH",("type","speed","reach","flags","value","health","weight","damage")),
 (b"AMMO",b"DATA"):("<fB3sIfH",("speed","flags","reserved","value","weight","damage")),
 (b"CLOT",b"DATA"):("<If",("value","weight")),
 (b"INGR",b"DATA"):("<f",("weight",)),
 (b"MISC",b"DATA"):("<If",("value","weight")),
 (b"BOOK",b"DATA"):("<BbIf",("flags","skill","value","weight")),
 (b"ARMO",b"DATA"):("<HIIf",("armor_rating_hundredths","value","health","weight")),
}
def oblivion_properties(signature,tag,raw):
    fmt,keys=OBLIVION_FIELDS[signature,tag]
    if len(raw)!=struct.calcsize(fmt):raise ValueError("Unexpected Oblivion field size")
    d=dict(zip(keys,struct.unpack(fmt,raw)))
    if any(isinstance(v,float) and not isfinite(v) for v in d.values()):raise ValueError("Nonfinite weight")
    return d

def edit_oblivion_properties(signature,tag,raw,**changes):
    d=oblivion_properties(signature,tag,raw)
    if set(changes)-set(d) or "reserved" in changes:raise ValueError("Unknown or reserved property")
    d.update(changes)
    for k,v in d.items():
        if k=="reserved":continue
        if k in ("weight","speed","reach"):
            if not isfinite(v) or not 0<=v<=1e6:raise ValueError("Invalid weight")
        elif type(v)!=int or (k=="skill" and not -1<=v<=20) or (k!="skill" and v<0):raise ValueError("Invalid "+k)
    fmt,keys=OBLIVION_FIELDS[signature,tag]
    try:return struct.pack(fmt,*(d[k] for k in keys))
    except (struct.error,OverflowError) as e:raise ValueError("Outside native range") from e
