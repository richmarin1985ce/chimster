"""Experimental FNV interior cell and static placement fixture writer."""
from pathlib import Path
import struct
from .fnv_content import ident,static,reference
from .fnv_patch import sub,record
from .fnv_world import cstr,group
from .fnv_bindings import Bindings
from .formids import FormIDs
from .fnv_records import scan
from .interior_layout import point

def export(spec,output,masters=(),allocator=None):
    if spec.get("schema")!=1 or set(spec)-{"schema","cells","statics"}:
        raise ValueError("invalid interior specification")
    p=Path(output)
    if p.suffix.lower()!=".esp" or p.exists() or p.is_symlink():
        raise ValueError("expected new ESP")
    cells=spec["cells"];statics=spec.get("statics",[])
    if not isinstance(cells,list) or not 1<=len(cells)<=10000 or not isinstance(statics,list) or len(statics)>50000:
        raise ValueError("interior size limit")
    b=Bindings(masters,p);ids=allocator or FormIDs(p.name)
    base={};top=[];blocks={};used=set();expected={}
    def alloc(kind,key):
        ident(key)
        return b.slot|ids.get(kind+"/"+key.casefold())
    def register(key):
        ident(key)
        if key.casefold() in used:raise ValueError("duplicate editor ID")
        used.add(key.casefold())
    for s in statics:
        register(s["id"]);fid=alloc("STAT",s["id"])
        base[s["id"]]=fid;top.append(static(fid,s));expected[fid]="STAT"
    count=0;groups=1+bool(top)
    for cell in cells:
        if set(cell)-{"id","title","placements"}:raise ValueError("unknown cell fields")
        register(cell["id"]);cid=alloc("CELL",cell["id"]);expected[cid]="CELL"
        payload=sub(b"EDID",ident(cell["id"]))+sub(b"FULL",cstr(cell["title"]))+sub(b"DATA",b"\x01")
        raw=record(b"CELL",payload,cid)
        buckets={8:[],9:[]}
        for r in cell.get("placements",[]):
            if set(r)-{"id","base","position","yaw","scale","persistent"}:raise ValueError("unknown placement field")
            count+=1
            if count>50000:raise ValueError("placement limit")
            persistent=r.get("persistent",False)
            if type(persistent) is not bool:raise ValueError("invalid persistence flag")
            ident(r["id"])
            fid=b.slot|ids.get("REFR/"+cell["id"].casefold()+"/"+r["id"].casefold())
            target=base[r["base"]] if isinstance(r["base"],str) else b.resolve(r["base"],{"STAT"})
            x,y,z=point(r["position"])
            placed=reference(fid,target,x,y,z,r.get("yaw",0.),r.get("scale",1.))
            if persistent:
                placed=placed[:8]+struct.pack("<I",0x400)+placed[12:]
            buckets[8 if persistent else 9].append(placed);expected[fid]="REFR"
        children=b"".join(group(kind,cid,b"".join(rows)) for kind,rows in buckets.items() if rows)
        if children:
            raw+=group(6,cid,children);groups+=1+sum(bool(rows) for rows in buckets.values())
        local=cid&0xffffff
        blocks.setdefault(local%10,{}).setdefault((local//10)%10,[]).append(raw)
    nested=[]
    for block,subs in sorted(blocks.items()):
        chunks=[group(3,subblock,b"".join(rows)) for subblock,rows in sorted(subs.items())]
        nested.append(group(2,block,b"".join(chunks)));groups+=1+len(chunks)
    body=(group(0,b"STAT",b"".join(top)) if top else b"")+group(0,b"CELL",b"".join(nested))
    header=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,len(expected)+groups,ids.next))+sub(b"CNAM",b"Chimster\0")+b.header())
    b.check();created=False
    try:
        with p.open("xb") as stream:
            created=True;stream.write(header+body)
        report=scan(p)
        if len(report["records"])!=len(expected) or {b.slot|r["local_id"]:r["signature"] for r in report["records"]}!=expected:
            raise ValueError("interior record identity mismatch")
        from .world_validator import validate
        validation=validate([*b.paths,p])
        if not validation["valid"]:raise ValueError("interior hierarchy validation failed")
        b.check()
    except Exception:
        if created:p.unlink()
        raise
    return {"output":str(p),"cells":len(cells),"placements":count,"records":len(expected),"scope":"experimental generated FNV interiors; no native lighting, doors, navmesh or retail runtime certification"}
