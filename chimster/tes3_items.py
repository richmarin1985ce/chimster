"""TES3 item records use named identities, not FormIDs."""
import struct
from math import isfinite
from .native_parser import parse,subrecords
from .native_profiles import PROFILES

ITEMS={b"SPEL",b"NPC_",b"CREA",b"LEVC",b"ENCH",b"BOOK",b"WEAP",b"ARMO",b"CLOT",b"ALCH",b"INGR",b"MISC",b"CONT",b"LEVI",b"APPA",b"LOCK",b"PROB",b"REPA",b"LIGH"}

def inspect(profile,data):
    if PROFILES[profile].family!="TES3":raise ValueError("Expected TES3")
    rows=[]
    for node in parse(profile,data):
        if node.signature not in ITEMS:continue
        row={"signature":node.signature.decode(),"raw":[],"fields":{},"issues":[]}
        for tag,v in subrecords(profile,node):
            k=tag.decode("ascii");row["raw"].append((k,v.hex()))
            if tag==b"ENAM" and node.signature in (b"SPEL",b"ENCH",b"ALCH"):
                try:row.setdefault("effects",[]).append(magic_effect(v))
                except ValueError as e:row["issues"].append(str(e))
                continue
            if tag==b"DELE":row["deleted"]=True
            if tag in (b"NAME",b"FNAM",b"MODL",b"ITEX",b"TEXT",b"SCRI",b"ENAM"):
                row["fields"].setdefault(k,[]).append(v.rstrip(b"\0").decode("cp1252",errors="replace"))
            if tag==b"BKDT":
                if len(v)!=20:row["issues"].append("Invalid BKDT length");continue
                w,val,scroll,skill,enchant=struct.unpack("<fIIiI",v)
                if not isfinite(w):row["issues"].append("Nonfinite weight");continue
                row["book_data"]={"weight":w,"value":val,"scroll":scroll,"skill":skill,"enchantment_points":enchant}
        for tag,raw in row["raw"]:
            if tag=="NPCO":
                try:row.setdefault("inventory",[]).append(inventory_entry(bytes.fromhex(raw)))
                except ValueError as e:row["issues"].append(str(e))
            if row["signature"]=="INGR" and tag=="IRDT":
                try:row["properties"]=ingredient_data(bytes.fromhex(raw))
                except ValueError as e:row["issues"].append(str(e))
            if (row["signature"],tag) in SCHEMAS:
                try:row["properties"]=decode_properties(row["signature"],tag,bytes.fromhex(raw))
                except ValueError as e:row["issues"].append(str(e))
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

# Fixed-size TES3 data structures. Preserve flags and untouched values.
SCHEMAS={
 ("SPEL","SPDT"):("<3I",("type","cost","flags")),
 ("CONT","CNDT"):("<f",("capacity",)),
 ("APPA","AADT"):("<IffI",("type","quality","weight","value")),
 ("LOCK","LKDT"):("<fIfI",("weight","value","quality","uses")),
 ("PROB","PBDT"):("<fIfI",("weight","value","quality","uses")),
 ("REPA","RIDT"):("<fIIf",("weight","value","uses","quality")),
 ("LIGH","LHDT"):("<fIiIII",("weight","value","duration","radius","color_raw","flags")),
 ("CLOT","CTDT"):("<IfHH",("type","weight","value","enchantment_points")),
 ("ENCH","ENDT"):("<4I",("type","cost","charge","flags")),
 ("WEAP","WPDT"):("<fIHHffH6BI",("weight","value","type","health","speed","reach","enchantment_points","chop_min","chop_max","slash_min","slash_max","thrust_min","thrust_max","flags")),
 ("ARMO","AODT"):("<IfIIII",("type","weight","value","health","enchantment_points","armor_rating")),
 ("MISC","MCDT"):("<fII",("weight","value","unknown")),
 ("ALCH","ALDT"):("<fII",("weight","value","flags")),
}
def decode_properties(signature,tag,raw):
    fmt,keys=SCHEMAS[signature,tag]
    if len(raw)!=struct.calcsize(fmt):raise ValueError("Unexpected "+tag+" length")
    values=dict(zip(keys,struct.unpack(fmt,raw)))
    if any(isinstance(v,float) and not isfinite(v) for v in values.values()):raise ValueError("Nonfinite item property")
    return values

def edit_properties(signature,tag,raw,**changes):
    values=decode_properties(signature,tag,raw)
    if set(changes)-set(values) or "unknown" in changes:raise ValueError("Unsupported property")
    values.update(changes)
    for key,v in values.items():
        if key in ("weight","speed","reach","quality","capacity"):
            if not isfinite(v) or not 0<=v<=1e6:raise ValueError("Invalid "+key)
        elif key=="duration":
            if type(v)!=int or not -1<=v<=2147483647:raise ValueError("Invalid duration")
        elif type(v)!=int or v<0:raise ValueError("Invalid "+key)
    if signature=="CLOT" and values["type"]>9:raise ValueError("Invalid clothing type")
    if signature=="ENCH" and values["type"]>3:raise ValueError("Invalid enchantment type")
    if signature=="WEAP":
        for attack in ("chop","slash","thrust"):
            if values[attack+"_min"]>values[attack+"_max"]:raise ValueError("Inverted damage range")
    fmt,keys=SCHEMAS[signature,tag]
    try:return struct.pack(fmt,*(values[k] for k in keys))
    except (struct.error,OverflowError) as e:raise ValueError("Property outside native range") from e

def ingredient_data(raw):
    if len(raw)!=56:raise ValueError("Invalid IRDT length")
    weight,value,*rest=struct.unpack("<fi12i",raw)
    if not isfinite(weight):raise ValueError("Invalid ingredient weight")
    return {"weight":weight,"value":value,"effects":[{"effect":rest[i],"skill":rest[4+i],"attribute":rest[8+i]} for i in range(4)]}

def edit_ingredient(raw,*,weight=None,value=None):
    data=ingredient_data(raw)
    w=data["weight"] if weight is None else weight
    v=data["value"] if value is None else value
    if not isfinite(w) or not 0<=w<=1e6 or type(v)!=int or not 0<=v<=2147483647:raise ValueError("Invalid ingredient properties")
    return struct.pack("<fi",w,v)+raw[8:]

def inventory_entry(raw):
    if len(raw)!=36:raise ValueError("Invalid NPCO size")
    count,name=struct.unpack("<i32s",raw)
    return {"count":count,"item":name.split(b"\0",1)[0].decode("cp1252")}

def edit_inventory_count(raw,count):
    inventory_entry(raw)
    if type(count)!=int or not -2147483648<=count<=2147483647:raise ValueError("Invalid count")
    return struct.pack("<i",count)+raw[4:]

def magic_effect(raw):
    if len(raw)!=24:raise ValueError("Invalid ENAM effect size")
    effect,skill,attribute,range_,area,duration,minimum,maximum=struct.unpack("<Hbb5i",raw)
    return dict(effect=effect,skill=skill,attribute=attribute,range=range_,area=area,duration=duration,minimum=minimum,maximum=maximum)

def edit_magic_effect(raw,**changes):
    d=magic_effect(raw)
    if set(changes)-set(d):raise ValueError("Unknown effect property")
    d.update(changes)
    if any(type(v)!=int for v in d.values()):raise ValueError("Expected integer")
    if d["range"] not in (0,1,2) or any(d[k]<0 for k in ("area","duration","minimum","maximum")) or d["minimum"]>d["maximum"]:raise ValueError("Invalid effect parameters")
    try:return struct.pack("<Hbb5i",*(d[k] for k in ("effect","skill","attribute","range","area","duration","minimum","maximum")))
    except struct.error as e:raise ValueError("Effect property outside native range") from e
