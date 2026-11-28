"""Offline review of imported road centerlines; never infer intersections or bridge levels."""
import argparse
import json
import math
from collections import defaultdict, Counter
from pathlib import Path

CLASSES={"S1100":"primary","S1200":"secondary","S1400":"local",
         "S1500":"trail","S1630":"ramp","S1640":"service",
         "S1710":"walkway","S1720":"stairs","S1730":"alley",
         "S1740":"private","S1750":"internal","S1780":"parking"}

def review(data):
    if data.get("schema")!="chimster.local-roads.v1":
        raise ValueError("unsupported road source")
    groups=defaultdict(list)
    counts=Counter()
    records=[]
    ids=set()
    for f in data["features"]:
        ident=f["id"]
        if not isinstance(ident,str) or not ident or ident in ids:
            raise ValueError("missing or duplicate source id")
        ids.add(ident)
        g=f["geometry"]
        if g["type"]!="LineString": raise ValueError("expected LineString")
        coords=g["coordinates"]
        if len(coords)<2 or any(len(p)!=2 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in p) for p in coords):
            raise ValueError("invalid road coordinates")
        points=tuple(tuple(p) for p in coords)
        length=sum(math.dist(a,b) for a,b in zip(points,points[1:]))
        if length<=0: raise ValueError("zero length road")
        category=CLASSES.get(f.get("mtfcc"),"unclassified")
        counts[category]+=1
        # Exact full centerline matches only. Preserve every source entry.
        # Reversed orientation is a review candidate, never a deletion.
        key=min(points,points[::-1])
        groups[key].append(ident)
        records.append({"id":ident,"name":f.get("name",""),
                        "category":category,"length_playable_m":round(length,3),
                        "geometry_status":"source centerline; no terrain or elevation binding"})
    return {"schema":"chimster.road-review.v1","source_count":len(records),
            "category_counts":dict(counts),"records":records,
            "exact_duplicate_candidates":[sorted(ids) for ids in groups.values() if len(ids)>1],
            "status":"review only; grade separation, topology, near duplicates, source gaps and authored damage unresolved"}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args()
    result=review(json.loads(a.source.read_text(encoding="utf-8")))
    with a.output.open("x",encoding="utf-8") as f:
        json.dump(result,f,indent=2,allow_nan=False);f.write("\n")

if __name__=="__main__":main()
