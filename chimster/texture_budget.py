"""Conservative, game-specific landscape quadrant allocation reports."""
from collections import Counter
import struct,math
# Editor limits, not a claim about Remastered or other engine versions.
LIMITS={"oblivion":9,"fallout3":7,"newvegas":7}
def audit(parts,game):
    limit=LIMITS.get(game);q=[{"base":[],"alpha":[],"issues":[]} for _ in range(4)]
    active=None;issues=[]
    for tag,raw in parts:
        if tag in (b"BTXT",b"ATXT"):
            active=None
            if len(raw)!=8:issues.append("invalid layer header size");continue
            texture,quad,_,layer=struct.unpack("<IBBh",raw)
            if quad>3:issues.append("invalid quadrant");continue
            entry={"texture":texture,"layer":layer}
            if tag==b"BTXT":q[quad]["base"].append(entry)
            else:
                entry["vertices"]=0;entry["opacity_sum"]=0.;entry["has_vtxt"]=False
                q[quad]["alpha"].append(entry);active=(quad,entry)
        elif tag==b"VTXT":
            if active is None:issues.append("VTXT without preceding ATXT");continue
            quad,entry=active;active=None;entry["has_vtxt"]=True
            if len(raw)%8:q[quad]["issues"].append("invalid VTXT length");continue
            seen=set()
            for pos,alpha in struct.iter_unpack("<H2xf",raw):
                if pos>=289 or pos in seen or not math.isfinite(alpha) or not 0<=alpha<=1:
                    q[quad]["issues"].append("invalid or duplicate alpha vertex");continue
                seen.add(pos);entry["opacity_sum"]+=alpha
            entry["vertices"]=len(seen)
        else:active=None
    report=[]
    for i,d in enumerate(q):
        entries=d["base"]+d["alpha"]
        # Reserve an implicit base if overlays exist but no explicit base.
        count=len(entries)+(1 if d["alpha"] and not d["base"] else 0)
        if len(d["base"])>1:d["issues"].append("multiple base layers")
        indices=[e["layer"] for e in d["alpha"]]
        if any(n<0 for n in indices) or len(indices)!=len(set(indices)):d["issues"].append("invalid or duplicate alpha index")
        repeated=[k for k,v in Counter(e["texture"] for e in entries).items() if v>1]
        report.append({"quadrant":i,"allocated":count,"limit":limit,"remaining":None if limit is None else limit-count,
                       "over_budget":limit is not None and count>limit,
                       "repeated_texture_ids":repeated,"distinct_texture_ids":len(set(e["texture"] for e in entries)),
                       "zero_opacity_layers":[e["layer"] for e in d["alpha"] if e["has_vtxt"] and e["opacity_sum"]==0],
                       "base":d["base"],"alpha":d["alpha"],"issues":d["issues"]})
    return {"game":game,"limit":limit,"quadrants":report,"issues":issues,
            "valid":limit is not None and not issues and not any(x["over_budget"] or x["issues"] for x in report),
            "scope":"allocated layer slots, including zero-opacity layers; not rendered coverage"}
def enforce_plan(game,layers):
    """Validate authoring allocations without removing or merging anything."""
    limit=LIMITS.get(game)
    if limit is None:raise ValueError("unverified quadrant limit")
    counts=Counter()
    for s in layers:
        x,y=s["cell"];q=s["quadrant"]
        if type(q) is not int or not 0<=q<4:raise ValueError("invalid quadrant")
        counts[(x,y,q)]+=1
    overflow=[(k,n+1) for k,n in sorted(counts.items()) if n+1>limit]
    if overflow:raise ValueError("quadrant texture budget exceeded: "+str(overflow[:8]))
    return {"limit":limit,"quadrants":[{"cell":[x,y],"quadrant":q,"allocated":n+1,"remaining":limit-n-1} for (x,y,q),n in sorted(counts.items())]}
