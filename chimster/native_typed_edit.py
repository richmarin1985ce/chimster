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
    if not raw or raw[-1:]!=b"\\0" or b"\\0" in raw[:-1]:
        raise ValueError("Expected inline NUL-terminated text")
    return raw[:-1].decode("cp1252")

def _one(parts,tag):
    matches=[raw for k,raw in parts if k==tag]
    if len(matches)!=1:raise ValueError("Expected unique discriminator")
    return matches[0]

def _inline_text(raw,value):
    _cstring(raw)
    if not isinstance(value,str) or "\\0" in value:raise ValueError("Invalid text")
    encoded=value.encode("cp1252")+b"\\0"
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
    elif profile in ("fallout3","new-vegas") and sig in (b"MISC",b"KEYM") and tag==b"DATA":
        if len(raw)!=8 or set(changes)-{"value","weight"}:raise ValueError("Unsupported item DATA")
        value,weight=struct.unpack("<if",raw)
        value=changes.get("value",value);weight=changes.get("weight",weight)
        if type(value)!=int or not 0<=value<=2147483647:raise ValueError("Invalid value")
        if type(weight) not in (int,float) or not math.isfinite(weight) or not 0<=weight<=1e6:raise ValueError("Invalid weight")
        updated=struct.pack("<if",value,weight)
    elif profile=="oblivion" and (sig,tag) in native_items.OBLIVION_FIELDS:
        updated=native_items.edit_oblivion_properties(sig,tag,raw,**changes)
    elif profile in ("fallout3","new-vegas") and (sig,tag)==(b"BOOK",b"DATA"):
        updated=native_items.edit_fallout_book_data(profile,raw,**changes)
    elif profile=="oblivion" and sig in (b"LVLI",b"LVLC",b"LVSP") and tag==b"LVLO":
        updated=native_items.edit_oblivion_leveled_entry(raw,**changes)
    else:raise ValueError("No registered typed editor for field")
    return replace(profile,data,path,tag,occurrence,raw,updated,revision)
