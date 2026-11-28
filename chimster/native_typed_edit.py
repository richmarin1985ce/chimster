"""Explicit dispatch for existing experimental typed payload adapters."""
from .native_parser import parse, subrecords
from .native_payload_edit import replace
from .native_profiles import PROFILES
from . import native_items, tes3_items

def edit(profile,data,path,tag,occurrence,changes,revision):
    if not path or any(type(i)!=int or i<0 for i in path):raise ValueError("Invalid path")
    nodes=parse(profile,data)
    for depth,index in enumerate(path):
        if index>=len(nodes):raise ValueError("Missing record")
        node=nodes[index]
        if depth<len(path)-1:
            if node.signature!=b"GRUP":raise ValueError("Invalid group path")
            nodes=node.children
    if node.signature==b"GRUP":raise ValueError("Expected record")
    matches=[v for k,v in subrecords(profile,node) if k==tag]
    if type(occurrence)!=int or not 0<=occurrence<len(matches):raise ValueError("Missing field")
    raw=matches[occurrence]
    sig=node.signature
    if PROFILES[profile].family=="TES3":
        if (sig,tag)==(b"BOOK",b"BKDT"):
            updated=tes3_items.edit_book_data(raw,**changes)
        elif sig in (b"SPEL",b"ENCH",b"ALCH") and tag==b"ENAM":
            updated=tes3_items.edit_magic_effect(raw,**changes)
        elif sig in (b"NPC_",b"CREA") and tag==b"AIDT":
            updated=tes3_items.edit_services(raw,**changes)
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
        elif (sig,tag)==(b"NPC_",b"NPDT"):
            updated=tes3_items.edit_npc_gold(raw,**changes)
        else:raise ValueError("No registered typed editor for field")
    elif profile=="oblivion" and (sig,tag) in native_items.OBLIVION_FIELDS:
        updated=native_items.edit_oblivion_properties(sig,tag,raw,**changes)
    elif profile in ("fallout3","new-vegas") and (sig,tag)==(b"BOOK",b"DATA"):
        updated=native_items.edit_fallout_book_data(profile,raw,**changes)
    elif profile=="oblivion" and sig in (b"LVLI",b"LVLC",b"LVSP") and tag==b"LVLO":
        updated=native_items.edit_oblivion_leveled_entry(raw,**changes)
    else:raise ValueError("No registered typed editor for field")
    return replace(profile,data,path,tag,occurrence,raw,updated,revision)
