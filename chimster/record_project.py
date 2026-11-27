"""Declarative top-level FNV records with explicit references and stable IDs."""
from pathlib import Path
import struct
from .fnv_world import group,cstr
from .fnv_patch import sub,record
from .fnv_content import ident,bounds,asset,static
from .fnv_bindings import Bindings
from .fnv_records import scan
from .record_schema import encode
from .formids import FormIDs
from .quest_editor import check_id
from .gameplay_records import KINDS as GAMEPLAY,encode as gameplay_encode
from .template_records import KINDS as TEMPLATES,clone
KINDS=("GMST","GLOB","CLAS","FACT","RACE","MGEF","SPEL","ARMO","CONT","MISC","STAT","WEAP","AMMO","NPC_","LVLN","KEYM","ALCH","LVLI","PACK","FLST","PERK","VTYP","ECZN","REPU")
def export(project,output,masters=(),allocator=None):
    p=Path(output)
    if p.suffix.lower()!=".esp" or p.exists() or p.is_symlink():raise ValueError("expected new ESP")
    if project.get("schema")!=1 or set(project)!={"schema","records"}:raise ValueError("invalid project")
    rows=project["records"]
    if not isinstance(rows,list) or not 1<=len(rows)<=50000:raise ValueError("invalid record count")
    b=Bindings(masters,p);a=allocator if allocator is not None else FormIDs(p.name);ids={};sigs={};groups={}
    from .identity_policy import reserve_hierarchy
    keys=[r["type"]+"/"+r["id"].casefold() for r in rows]
    if len(set(keys))!=len(keys):raise ValueError("duplicate stable key")
    reserve_hierarchy(a,dict.fromkeys(keys))
    for r in rows:
        k=r["id"];sig=r["type"]
        if sig not in KINDS or not check_id(k) or k.casefold() in ids:raise ValueError("invalid or duplicate record ID")
        ids[k.casefold()]=b.slot|a.get(sig+"/"+k.casefold());sigs[k.casefold()]=sig
    def link(ref,kinds=None):
        kinds=kinds or (set(KINDS)|{"BOOK","NOTE","ALCH","CREA","QUST","DIAL","REFR","ACHR","CELL"})
        if isinstance(ref,str):
            if ref.casefold() not in ids:raise ValueError("unknown local reference "+ref)
            if sigs[ref.casefold()] not in kinds:raise ValueError("wrong local reference type: "+ref)
            return ids[ref.casefold()]
        # Narrow allowed base types. No opaque or deleted links.
        return b.resolve(ref,kinds)
    check_list_cycles(rows)
    for r in rows:
        sig=r["type"];k=r["id"];f=r["fields"];fid=ids[k.casefold()]
        body=sub(b"EDID",ident(k))
        if sig in TEMPLATES:
            raw=record(sig.encode(),clone(sig,k,f,b,link),fid)
        elif sig=="STAT":
            if set(f)!={"model","bounds"}:raise ValueError("invalid static fields")
            raw=static(fid,{"id":k,**f})
        else:
            if sig=="GLOB":
                if set(f)!={"kind","value"} or f["kind"] not in {"s","l","f"}:raise ValueError("invalid global")
                body+=sub(b"FNAM",f["kind"].encode())+sub(b"FLTV",encode({"s":"short_global","l":"long_global","f":"float"}[f["kind"]],f["value"]))
            elif sig=="GMST":
                if set(f)!={"value"} or k[0] not in "sif":raise ValueError("invalid game setting")
                body+=sub(b"DATA",encode({"s":"text","i":"int","f":"float"}[k[0]],f["value"]))
            elif sig=="MISC":
                if set(f)!={"title","model","bounds","value","weight"}:raise ValueError("invalid item")
                body+=bounds(f["bounds"])+sub(b"FULL",cstr(f["title"]))+sub(b"MODL",asset(f["model"],".nif"))+sub(b"DATA",encode("item",{"value":f["value"],"weight":f["weight"]}))
            elif sig in GAMEPLAY:
                body+=gameplay_encode(sig,f,link)
            elif sig=="FLST":
                if set(f)!={"entries"} or not isinstance(f["entries"],list) or len(f["entries"])>50000:raise ValueError("invalid list")
                refs=[link(v) for v in f["entries"]]
                if fid in refs:raise ValueError("self-referencing form list")
                body+=b"".join(sub(b"LNAM",struct.pack("<I",v)) for v in refs)
            raw=record(sig.encode(),body,fid)
        groups.setdefault(sig,[]).append(raw)
    data=b"".join(group(0,s.encode(),b"".join(groups[s])) for s in KINDS if s in groups)
    header=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,len(rows)+len(groups),a.next))+sub(b"CNAM",b"Chimster\0")+b.header())
    b.check()
    with p.open("xb") as f:f.write(header+data)
    try:
        r=scan(p)
        if len(r["records"])!=len(rows) or {x["local_id"] for x in r["records"]}!={i&0xffffff for i in ids.values()}:raise ValueError("record identity mismatch")
        b.check()
    except Exception:
        p.unlink();raise
    return {"output":str(p),"records":ids,"masters":[x.name for x in b.paths],"status":"selected native record schemas; no engine certification"}
def remove(project,key):
    """Remove from an unexported project only; reject known local dependencies."""
    rows=project["records"];key=key.casefold()
    if sum(r["id"].casefold()==key for r in rows)!=1:raise ValueError("unknown or ambiguous ID")
    for r in rows:
        if r["id"].casefold()!=key and key in local_links(r):raise ValueError("record referenced by "+r["id"])
    if len(rows)==1:raise ValueError("project cannot be empty")
    return {"schema":1,"records":[r for r in rows if r["id"].casefold()!=key]}

def local_links(row):
    """Known symbolic reference fields only; external bindings are dictionaries."""
    f=row["fields"];sig=row["type"];refs=[]
    if sig=="FLST":refs.extend(f["entries"])
    if sig in {"LVLI","LVLN"}:refs.extend(e["ref"] for e in f["entries"]);refs.append(f.get("global"))
    if sig in {"CONT","NPC_"}:refs.extend(e["ref"] for e in f.get("items",[]))
    if sig=="FACT":refs.extend(e["ref"] for e in f.get("relations",[]));refs.append(f.get("reputation"))
    if sig=="ECZN":refs.append(f.get("owner"))
    if sig=="AMMO":refs.append(f.get("projectile"))
    if sig in {"PERK","SPEL","ALCH"}:refs.extend(e["ref"] for e in f["effects"])
    if sig=="ALCH":refs.extend(f.get(k) for k in ("withdrawal","consume_sound"))
    if sig=="NPC_":
        refs.extend(e["ref"] for e in f.get("factions",[]));refs.extend(f.get("packages",[]))
        refs.extend(f.get(k) for k in ("race","voice","class"))
    return {v.casefold() for v in refs if isinstance(v,str)}
def check_list_cycles(rows):
    from collections import deque
    lists={r["id"].casefold():r for r in rows if r["type"] in {"LVLI","LVLN"}}
    edges={k:local_links(v)&lists.keys() for k,v in lists.items()}
    counts={k:len(v) for k,v in edges.items()};rev={k:[] for k in lists}
    for k,v in edges.items():
        for x in v:rev[x].append(k)
    q=deque(k for k,n in counts.items() if n==0);seen=0
    while q:
        x=q.popleft();seen+=1
        for k in rev[x]:
            counts[k]-=1
            if not counts[k]:q.append(k)
    if seen!=len(lists):raise ValueError("cyclic local leveled lists")
