"""Selected FNV gameplay record schemas. All references are typed and resolved by caller."""
import struct
from .fnv_patch import sub
from .fnv_world import cstr
from .fnv_content import bounds,asset
from .record_schema import integer,number
ITEMS={"ARMO","AMMO","MISC","WEAP","BOOK","LVLI","KEYM","ALCH","NOTE","IMOD","CMNY","CCRD","CHIP"}
INVENTORY=ITEMS|{"LIGH","MSTT","STAT"}
KINDS={"REPU","CONT","LVLI","AMMO","ECZN","SPEL","PERK","FACT"}
def check(f,required,optional=()):
    if not isinstance(f,dict) or not set(required)<=set(f) or set(f)-set(required)-set(optional):raise ValueError("invalid gameplay fields")
def boolean(v):
    if type(v) is not bool:raise ValueError("expected boolean")
    return int(v)
def rows(v,limit=4096):
    if not isinstance(v,list) or len(v)>limit:raise ValueError("invalid collection")
    return v
def u32(v):return struct.pack("<I",v)
def inventory(entries,link):
    data=[];seen=set()
    for e in rows(entries):
        check(e,{"ref","count"});fid=link(e["ref"],INVENTORY)
        if fid in seen:raise ValueError("duplicate inventory entry")
        seen.add(fid);data.append(sub(b"CNTO",struct.pack("<Ii",fid,integer(e["count"],1,2**31-1))))
    return b"".join(data)
def common(f):
    return bounds(f["bounds"])+sub(b"FULL",cstr(f["title"]))+sub(b"MODL",asset(f["model"],".nif"))
def encode(sig,f,link):
    if sig=="REPU":
        check(f,{"title","value"})
        return sub(b"FULL",cstr(f["title"]))+sub(b"DATA",struct.pack("<f",number(f["value"],0,1e6)))
    if sig=="FACT":
        check(f,{"title"},{"hidden","evil","special_combat","track_crime","allow_sell","relations","ranks","reputation"})
        body=sub(b"FULL",cstr(f["title"]));seen=set()
        for r in rows(f.get("relations",[])):
            check(r,{"ref","modifier","reaction"});fid=link(r["ref"],{"FACT","RACE"})
            if fid in seen:raise ValueError("duplicate relation")
            seen.add(fid);body+=sub(b"XNAM",struct.pack("<IiI",fid,integer(r["modifier"],-100,100),integer(r["reaction"],0,3)))
        flags=sum(boolean(f.get(k,False))<<i for i,k in enumerate(("hidden","evil","special_combat")))
        flags2=sum(boolean(f.get(k,False))<<i for i,k in enumerate(("track_crime","allow_sell")))
        body+=sub(b"DATA",bytes((flags,flags2,0,0)));seen=set()
        for r in rows(f.get("ranks",[]),128):
            check(r,{"rank","male","female"});n=integer(r["rank"],0,127)
            if n in seen:raise ValueError("duplicate faction rank")
            seen.add(n);body+=sub(b"RNAM",struct.pack("<i",n))+sub(b"MNAM",cstr(r["male"]))+sub(b"FNAM",cstr(r["female"]))
        if "reputation" in f:body+=sub(b"WMI1",u32(link(f["reputation"],{"REPU"})))
        return body
    if sig=="CONT":
        check(f,{"title","model","bounds","items"},{"respawns","weight"})
        return common(f)+inventory(f["items"],link)+sub(b"DATA",struct.pack("<Bf",2*boolean(f.get("respawns",False)),number(f.get("weight",0),0,1000)))
    if sig=="LVLI":
        check(f,{"entries"},{"chance_none","flags","global","bounds"})
        entries=rows(f["entries"]);body=bounds(f.get("bounds",[0]*6))+sub(b"LVLD",bytes([integer(f.get("chance_none",0),0,100)]))+sub(b"LVLF",bytes([integer(f.get("flags",0),0,7)]))
        if "global" in f:body+=sub(b"LVLG",u32(link(f["global"],{"GLOB"})))
        else:body+=sub(b"LVLG",bytes(4))
        for e in sorted(entries,key=lambda r:r["level"]):
            check(e,{"ref","level","count"})
            body+=sub(b"LVLO",struct.pack("<h2xIh2x",integer(e["level"],1,32767),link(e["ref"],ITEMS),integer(e["count"],1,32767)))
        return body
    if sig=="AMMO":
        check(f,{"title","model","bounds","value","weight","speed","clip_rounds","projectile"},{"flags","projectiles_per_shot","short_name","abbreviation"})
        body=common(f)+sub(b"DATA",struct.pack("<fB3xiB",number(f["speed"],0,1e7),integer(f.get("flags",0),0,3),integer(f["value"],0,2**31-1),integer(f["clip_rounds"],1,255)))
        body+=sub(b"DAT2",struct.pack("<IIfIf",integer(f.get("projectiles_per_shot",1),1,255),link(f["projectile"],{"PROJ"}),number(f["weight"],0,1000),0,0.))
        if "short_name" in f:body+=sub(b"ONAM",cstr(f["short_name"]))
        if "abbreviation" in f:body+=sub(b"QNAM",cstr(f["abbreviation"]))
        return body
    if sig=="ECZN":
        check(f,{"minimum_level"},{"owner","rank","never_resets","match_below_min"})
        flags=boolean(f.get("never_resets",False))+2*boolean(f.get("match_below_min",False))
        return sub(b"DATA",struct.pack("<IbbBx",link(f["owner"],{"NPC_","FACT"}) if "owner" in f else 0,integer(f.get("rank",-1),-1,127),integer(f["minimum_level"],0,127),flags))
    if sig=="SPEL":
        check(f,{"title","type","effects"},{"flags"})
        effects=rows(f["effects"],128)
        if not effects:raise ValueError("actor effect requires base effect")
        body=sub(b"FULL",cstr(f["title"]))+sub(b"SPIT",struct.pack("<IIIB3x",integer(f["type"],0,10),0,0,integer(f.get("flags",0),0,255)))
        for e in effects:
            check(e,{"ref","magnitude","area","duration","range","actor_value"})
            body+=sub(b"EFID",u32(link(e["ref"],{"MGEF"})))+sub(b"EFIT",struct.pack("<IIIIi",integer(e["magnitude"],0,2**31-1),integer(e["area"],0,2**31-1),integer(e["duration"],0,2**31-1),integer(e["range"],0,2),integer(e["actor_value"],-1,72)))
        return body
    if sig=="PERK":
        check(f,{"title","description","ranks","minimum_level","effects"},{"trait","playable","hidden"})
        rank=integer(f["ranks"],1,255);effects=rows(f["effects"],128)
        if not effects:raise ValueError("perk requires explicit ability or quest effect")
        body=sub(b"FULL",cstr(f["title"]))+sub(b"DESC",cstr(f["description"]))+sub(b"DATA",bytes((boolean(f.get("trait",False)),integer(f["minimum_level"],0,255),rank,boolean(f.get("playable",True)),boolean(f.get("hidden",False)))))
        for e in effects:
            check(e,{"kind","ref","rank","priority"},{"stage"});k=e["kind"]
            if k not in {"ability","quest"}:raise ValueError("unsupported perk effect")
            body+=sub(b"PRKE",bytes((int(k=="ability"),integer(e["rank"],0,rank-1),integer(e["priority"],0,255))))
            if k=="ability":
                if "stage" in e:raise ValueError("stage only valid for quest effect")
                data=u32(link(e["ref"],{"SPEL"}))
            else:data=struct.pack("<IB3x",link(e["ref"],{"QUST"}),integer(e["stage"],0,255))
            body+=sub(b"DATA",data)+sub(b"PRKF",b"")
        return body
    raise ValueError("unsupported gameplay record")
