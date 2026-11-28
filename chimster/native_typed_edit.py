"""Explicit dispatch for existing experimental typed payload adapters."""
from .native_parser import parse, subrecords
from .native_payload_edit import replace
from .native_profiles import PROFILES
from . import native_items, tes3_items, tes3_actor_data, tes3_ai_packages

import math
import struct

# Explicit candidate layouts: no inheritance from FNV's variable record schemas.
_SCALAR_PROFILES = frozenset(("oblivion","fallout3","new-vegas","skyrim","skyrim-se","fallout4"))
_DISPLAY_RECORDS = frozenset((b"MISC",b"BOOK",b"WEAP",b"ARMO",b"NPC_",b"CONT",b"ACTI",b"DOOR",b"RACE",b"FACT",b"QUST",b"SPEL"))
_TES3_DISPLAY = frozenset((b"MISC",b"BOOK",b"WEAP",b"ARMO",b"NPC_",b"CREA",b"CONT",b"ACTI",b"DOOR",b"CLOT",b"ALCH",b"INGR",b"RACE",b"CLAS",b"FACT",b"SPEL"))

def _cstring(raw):
    if not raw or raw[-1:]!=b"\0" or b"\0" in raw[:-1]:
        raise ValueError("Expected inline NUL-terminated text")
    return raw[:-1].decode("cp1252")

def _one(parts,tag):
    matches=[raw for k,raw in parts if k==tag]
    if len(matches)!=1:raise ValueError("Expected unique discriminator")
    return matches[0]

def _inline_text(raw,value):
    _cstring(raw)
    if not isinstance(value,str) or "\0" in value:raise ValueError("Invalid text")
    encoded=value.encode("cp1252")+b"\0"
    if len(encoded)>65535:raise ValueError("Text field too long")
    return encoded

def _scalar(kind,raw,value):
    if kind=="text":return _inline_text(raw,value)
    if len(raw)!=4:raise ValueError("Unsupported scalar size")
    if kind=="int":
        if type(value)!=int or not -2**31<=value<2**31:raise ValueError("Invalid integer")
        return struct.pack("<i",value)
    if kind in ("short","long"):
        limit=(-32768,32767) if kind=="short" else (-16777216,16777216)
        if type(value)!=int or not limit[0]<=value<=limit[1]:raise ValueError("Invalid exact global integer")
    elif type(value) not in (int,float) or not -3.4e38<=value<=3.4e38 or not math.isfinite(value):
        raise ValueError("Invalid finite scalar")
    return struct.pack("<f",value)

def _common_kind(profile,sig,tag,parts):
    if profile=="morrowind":
        if sig in _TES3_DISPLAY and tag==b"FNAM":return "text"
        if sig==b"GLOB" and tag==b"FLTV":
            return {b"s":"short",b"l":"long",b"f":"float"}.get(_one(parts,b"FNAM"))
        if sig==b"GMST":
            name=_cstring(_one(parts,b"NAME"))
            return {("s",b"STRV"):"text",("i",b"INTV"):"int",("f",b"FLTV"):"float"}.get((name[:1],tag))
        return None
    if profile not in _SCALAR_PROFILES:return None
    if sig in _DISPLAY_RECORDS and tag==b"FULL":return "text"
    if sig==b"GMST" and tag==b"DATA":
        name=_cstring(_one(parts,b"EDID"))
        return {"s":"text","i":"int","f":"float"}.get(name[:1])
    if sig==b"GLOB" and tag==b"FLTV":
        return {b"s":"short",b"l":"long",b"f":"float"}.get(_one(parts,b"FNAM"))
    return None

def common_fields(profile,node,localized=False):
    """Discover conservative editable scalar fields; opaque fields are omitted."""
    parts=list(subrecords(profile,node));result=[]
    for tag,raw in parts:
        try:
            kind=_common_kind(profile,node.signature,tag,parts)
            if not kind or (localized and kind=="text") or sum(k==tag for k,_ in parts)!=1:continue
            value=_cstring(raw) if kind=="text" else struct.unpack("<i" if kind=="int" else "<f",raw)[0]
            if kind in ("short","long"):
                if not math.isfinite(value) or not value.is_integer():continue
                value=int(value)
            _scalar(kind,raw,value)
            result.append({"tag":tag.decode("ascii"),"occurrence":0,"type":kind,"value":value})
        except (ValueError,UnicodeError,struct.error,OverflowError):continue
    return result

def _fixed_properties(profile,sig,tag,raw):
    """Candidate exact-length property adapters, with no reference-bearing bytes exposed."""
    if profile=="morrowind":
        key=(sig.decode("ascii"),tag.decode("ascii"))
        if key in tes3_items.SCHEMAS:
            return {k:v for k,v in tes3_items.decode_properties(*key,raw).items() if k!="unknown"}
        if (sig,tag)==(b"BOOK",b"BKDT"):
            return dict(zip(("weight","value","scroll","skill","enchantment_points"),struct.unpack("<fIIiI",raw)))
        if (sig,tag)==(b"INGR",b"IRDT"):
            d=tes3_items.ingredient_data(raw);return {k:d[k] for k in ("weight","value")}
        if sig in (b"NPC_",b"CREA") and tag==b"NPDT":return tes3_actor_data.decode(sig,raw)
        if sig in (b"NPC_",b"CREA") and tag==b"AIDT":
            return {**tes3_actor_data.ai_decode(raw),**tes3_items.decode_services(raw)}
        if sig in (b"NPC_",b"CREA",b"CONT") and tag==b"NPCO":
            return {"count":tes3_items.inventory_entry(raw)["count"]}
        if sig in (b"SPEL",b"ENCH",b"ALCH") and tag==b"ENAM":
            return tes3_items.magic_effect(raw)
        if sig in (b"LEVI",b"LEVC") and tag==b"INTV":return {"level":struct.unpack("<H",raw)[0]}
        if sig in (b"LEVI",b"LEVC") and tag==b"NNAM":return {"chance":struct.unpack("<B",raw)[0]}
    if profile=="oblivion":
        if (sig,tag) in native_items.OBLIVION_FIELDS:
            return {k:v for k,v in native_items.oblivion_properties(sig,tag,raw).items() if k!="reserved"}
    if profile in ("fallout3","new-vegas") and (sig,tag)==(b"BOOK",b"DATA"):
        flags,skill,value,weight=struct.unpack("<Bbif",raw)
        return {"skill":skill,"value":value,"weight":weight,"untakeable":bool(flags&2)}
    if profile in ("oblivion","fallout3","new-vegas") and sig in (b"LVLI",b"LVLC",b"LVLN",b"LVSP") and tag==b"LVLO":
        level,_,_,count,_=struct.unpack("<h2sIh2s",raw)
        return {"level":level,"count":count}
    spec=_property_layout(profile,sig,tag)
    if spec is not None:
        fmt,keys=spec
        return dict(zip(keys,struct.unpack(fmt,raw)))
    return None

def _property_layout(profile,sig,tag):
    if profile not in _SCALAR_PROFILES:return None
    if tag==b"DATA":
        if profile in ("fallout3","new-vegas") and sig in (b"MISC",b"KEYM"):
            return "<if",("value","weight")
        if profile in ("fallout3","new-vegas") and sig==b"WEAP":
            return "<iifhB",("value","health","weight","damage","clip_size")
        if profile in ("fallout3","new-vegas") and sig==b"ARMO":
            return "<iif",("value","health","weight")
        if profile in ("skyrim","skyrim-se") and sig==b"WEAP":
            return "<IfH",("value","weight","damage")
        if profile in ("skyrim","skyrim-se") and sig in (b"MISC",b"ARMO",b"KEYM"):
            return "<If",("value","weight")
        if profile=="fallout4" and sig==b"MISC":
            return "<If",("value","weight")
    return None

def _edit_fixed(profile,sig,tag,raw,changes):
    spec=_property_layout(profile,sig,tag)
    if spec is None:return None
    fmt,keys=spec
    if set(changes)-set(keys):raise ValueError("Unsupported property")
    if len(raw)!=struct.calcsize(fmt):raise ValueError("Unexpected property layout size")
    values=dict(zip(keys,struct.unpack(fmt,raw)))
    values.update(changes)
    for key,v in changes.items():
        if key=="weight":
            if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1e6:raise ValueError("Invalid weight")
        elif type(v)!=int or v<0:raise ValueError("Invalid integer property")
    try:return struct.pack(fmt,*(values[k] for k in keys))
    except (struct.error,OverflowError) as exc:raise ValueError("Property outside native range") from exc

def property_fields(profile,node,localized=False):
    """Field-level editor rows, including repeated typed inventory/effect entries."""
    parts=list(subrecords(profile,node));counts={}
    tes3=PROFILES[profile].family=="TES3"
    if (tes3 and (any(k==b"DELE" for k,_ in parts) or struct.unpack_from("<I",node.header,12)[0]&0x20)) or (not tes3 and struct.unpack_from("<I",node.header,8)[0]&0x20):return []
    rows=common_fields(profile,node,localized)
    for tag,raw in parts:
        occurrence=counts.get(tag,0);counts[tag]=occurrence+1
        try:
            if tag not in (b"CNTO",b"NPCO",b"ENAM",b"LVLO",b"INTV") and sum(k==tag for k,_ in parts)!=1:continue
            values=_fixed_properties(profile,node.signature,tag,raw)
            if values is None and profile in _SCALAR_PROFILES and tag==b"CNTO" and node.signature in (b"NPC_",b"CONT",b"CREA"):
                if len(raw)==8:values={"count":struct.unpack_from("<i",raw,4)[0]}
            if values is not None and all(type(v) in (int,float,bool) and (type(v)!=float or math.isfinite(v)) for v in values.values()):
                rows.append({"tag":tag.decode("ascii"),"occurrence":occurrence,"type":"properties","value":values})
        except (ValueError,UnicodeError,struct.error,OverflowError):continue
    return rows

def edit(profile,data,path,tag,occurrence,changes,revision):
    if not path or any(type(i)!=int or i<0 for i in path):raise ValueError("Invalid path")
    if not isinstance(changes,dict) or not changes:raise ValueError("Expected nonempty typed changes")
    nodes=parse(profile,data)
    root=nodes[0] if nodes else None
    localized=bool(root and root.signature==b"TES4" and struct.unpack_from("<I",root.header,8)[0]&0x80)
    for depth,index in enumerate(path):
        if index>=len(nodes):raise ValueError("Missing record")
        node=nodes[index]
        if depth<len(path)-1:
            if node.signature!=b"GRUP":raise ValueError("Invalid group path")
            nodes=node.children
    if node.signature==b"GRUP":raise ValueError("Expected record")
    if node.signature in (b"TES3",b"TES4"):raise ValueError("Plugin header is not editable")
    parts=list(subrecords(profile,node))
    tes3=PROFILES[profile].family=="TES3"
    if (tes3 and (any(k==b"DELE" for k,_ in parts) or struct.unpack_from("<I",node.header,12)[0]&0x20)) or (not tes3 and struct.unpack_from("<I",node.header,8)[0]&0x20):
        raise ValueError("Deleted record is not editable")
    matches=[v for k,v in parts if k==tag]
    if type(occurrence)!=int or not 0<=occurrence<len(matches):raise ValueError("Missing field")
    raw=matches[occurrence]
    sig=node.signature
    kind=_common_kind(profile,sig,tag,parts)
    if kind:
        if len(matches)!=1 or set(changes)!={"value"} or (localized and kind=="text"):
            raise ValueError("Ambiguous or localized scalar field")
        updated=_scalar(kind,raw,changes["value"])
    elif PROFILES[profile].family=="TES3":
        if (sig,tag)==(b"BOOK",b"BKDT"):
            updated=tes3_items.edit_book_data(raw,**changes)
        elif sig in (b"SPEL",b"ENCH",b"ALCH") and tag==b"ENAM":
            updated=tes3_items.edit_magic_effect(raw,**changes)
        elif sig in (b"NPC_",b"CREA") and tag==b"AIDT":
            behavior={k:v for k,v in changes.items() if k in ("hello","fight","flee","alarm")}
            services={k:v for k,v in changes.items() if k not in behavior}
            updated=tes3_items.edit_services(tes3_actor_data.ai_edit(raw,**behavior),**services)
        elif sig==b"CONT" and tag==b"FLAG":
            updated=tes3_items.edit_container_flags(raw,**changes)
        elif (sig.decode("ascii"),tag.decode("ascii")) in tes3_items.SCHEMAS:
            updated=tes3_items.edit_properties(sig.decode("ascii"),tag.decode("ascii"),raw,**changes)
        elif (sig,tag)==(b"INGR",b"IRDT"):
            updated=tes3_items.edit_ingredient(raw,**changes)
        elif sig in (b"NPC_",b"CREA",b"CONT") and tag==b"NPCO":
            updated=tes3_items.edit_inventory_count(raw,**changes)
        elif sig in (b"LEVI",b"LEVC") and tag==b"INTV":
            updated=tes3_items.edit_leveled_level(raw,**changes)
        elif sig in (b"LEVI",b"LEVC") and tag==b"NNAM":
            updated=tes3_items.edit_chance_none(raw,**changes)
        elif sig in (b"NPC_",b"CREA") and tag==b"NPDT":
            updated=tes3_actor_data.edit(sig,raw,**changes)
        elif sig in (b"NPC_",b"CREA") and tag in tes3_ai_packages.FORMATS:
            updated=tes3_ai_packages.edit(tag,raw,**changes)
        elif sig in (b"NPC_",b"CREA") and tag==b"FLAG":
            updated=tes3_actor_data.flags_edit(sig,raw,**changes)
        else:raise ValueError("No registered typed editor for field")
    elif _property_layout(profile,sig,tag) is not None:
        if len(matches)!=1:raise ValueError("Ambiguous fixed property field")
        updated=_edit_fixed(profile,sig,tag,raw,changes)
    elif profile in _SCALAR_PROFILES and tag==b"CNTO" and sig in (b"NPC_",b"CONT",b"CREA"):
        if len(raw)!=8 or set(changes)!={"count"} or type(changes["count"])!=int or not 1<=changes["count"]<=2147483647:
            raise ValueError("Invalid inventory count")
        updated=raw[:4]+struct.pack("<i",changes["count"])
    elif profile=="oblivion" and (sig,tag) in native_items.OBLIVION_FIELDS:
        updated=native_items.edit_oblivion_properties(sig,tag,raw,**changes)
    elif profile in ("fallout3","new-vegas") and (sig,tag)==(b"BOOK",b"DATA"):
        updated=native_items.edit_fallout_book_data(profile,raw,**changes)
    elif profile in ("oblivion","fallout3","new-vegas") and sig in (b"LVLI",b"LVLC",b"LVLN",b"LVSP") and tag==b"LVLO":
        updated=native_items.edit_oblivion_leveled_entry(raw,**changes)
    else:raise ValueError("No registered typed editor for field")
    return replace(profile,data,path,tag,occurrence,raw,updated,revision)
