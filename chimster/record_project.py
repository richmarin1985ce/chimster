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
KINDS=("GMST","GLOB","FACT","MISC","STAT","FLST")
def export(project,output,masters=(),allocator=None):
    p=Path(output)
    if p.suffix.lower()!=".esp" or p.exists() or p.is_symlink():raise ValueError("expected new ESP")
    if project.get("schema")!=1 or set(project)!={"schema","records"}:raise ValueError("invalid project")
    rows=project["records"]
    if not isinstance(rows,list) or not 1<=len(rows)<=50000:raise ValueError("invalid record count")
    b=Bindings(masters,p);a=allocator if allocator is not None else FormIDs(p.name);ids={};sigs={};groups={}
    for r in rows:
        k=r["id"];sig=r["type"]
        if sig not in KINDS or not check_id(k) or k.casefold() in ids:raise ValueError("invalid or duplicate record ID")
        ids[k.casefold()]=b.slot|a.get(sig+"/"+k.casefold());sigs[k.casefold()]=sig
    def link(ref):
        if isinstance(ref,str):
            if ref.casefold() not in ids:raise ValueError("unknown local reference "+ref)
            return ids[ref.casefold()]
        # Narrow allowed base types. No opaque or deleted links.
        return b.resolve(ref,set(KINDS)|{"BOOK","NOTE","WEAP","ARMO","AMMO","ALCH","NPC_","CREA","QUST","DIAL","REFR","ACHR","CELL"})
    for r in rows:
        sig=r["type"];k=r["id"];f=r["fields"];fid=ids[k.casefold()]
        body=sub(b"EDID",ident(k))
        if sig=="STAT":
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
            elif sig=="FACT":
                if set(f)!={"title"}:raise ValueError("invalid faction")
                body+=sub(b"FULL",cstr(f["title"]))+sub(b"DATA",bytes(4))
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
        if r["type"]=="FLST" and any(isinstance(v,str) and v.casefold()==key for v in r["fields"]["entries"]):raise ValueError("record referenced by "+r["id"])
    if len(rows)==1:raise ValueError("project cannot be empty")
    return {"schema":1,"records":[r for r in rows if r["id"].casefold()!=key]}
