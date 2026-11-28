"""TES3 item records use named identities, not FormIDs."""
import struct
from math import isfinite
from .native_parser import parse,subrecords
from .native_profiles import PROFILES

ITEMS={b"BOOK",b"WEAP",b"ARMO",b"CLOT",b"ALCH",b"INGR",b"MISC",b"CONT",b"LEVI",b"APPA",b"LOCK",b"PROB",b"REPA",b"LIGH"}

def inspect(profile,data):
    if PROFILES[profile].family!="TES3":raise ValueError("Expected TES3")
    rows=[]
    for node in parse(profile,data):
        if node.signature not in ITEMS:continue
        row={"signature":node.signature.decode(),"raw":[],"fields":{},"issues":[]}
        for tag,v in subrecords(profile,node):
            k=tag.decode("ascii");row["raw"].append((k,v.hex()))
            if tag==b"DELE":row["deleted"]=True
            if tag in (b"NAME",b"FNAM",b"MODL",b"ITEX",b"TEXT",b"SCRI",b"ENAM"):
                row["fields"].setdefault(k,[]).append(v.rstrip(b"\0").decode("cp1252",errors="replace"))
            if tag==b"BKDT":
                if len(v)!=20:row["issues"].append("Invalid BKDT length");continue
                w,val,scroll,skill,enchant=struct.unpack("<fIIiI",v)
                if not isfinite(w):row["issues"].append("Nonfinite weight");continue
                row["book_data"]={"weight":w,"value":val,"scroll":scroll,"skill":skill,"enchantment_points":enchant}
        names=row["fields"].get("NAME",[])
        if len(names)==1 and names[0]:row["identity"]=names[0].casefold()
        else:row["issues"].append("Missing or ambiguous NAME")
        rows.append(row)
    return {"profile":profile,"items":rows}

def edit_book_data(raw,**changes):
    if len(raw)!=20:raise ValueError("Invalid BKDT")
    keys=("weight","value","scroll","skill","enchantment_points")
    values=dict(zip(keys,struct.unpack("<fIIiI",raw)))
    if set(changes)-set(keys):raise ValueError("Unknown book property")
    values.update(changes)
    w,v,s,k,e=(values[key] for key in keys)
    if not isfinite(w) or not 0<=w<=1e6:raise ValueError("Invalid weight")
    if any(type(x)!=int or not 0<=x<=0xffffffff for x in (v,e)):raise ValueError("Invalid unsigned property")
    if type(s)!=int or s not in (0,1) or type(k)!=int or not -1<=k<=26:raise ValueError("Invalid scroll or skill")
    return struct.pack("<fIIiI",w,v,s,k,e)
