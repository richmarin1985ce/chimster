"""Portable occlusion/multibound review, no assumed native serialization or unsafe culling."""
from .interior_layout import bounds,contains,point,validate
from .portal_clip import ordered

def audit(layout,spec,objects=()):
    if not validate(layout)["valid"]:raise ValueError("invalid layout")
    if set(spec)-{"multibounds","occluders"}:raise ValueError("unknown visibility field")
    rooms={r["id"]:bounds(r) for r in layout["rooms"]};portals=layout.get("portals",[])
    groups={};seen=set();issues=[]
    for row in spec.get("multibounds",[]):
        if set(row)!={"id","room","min","max"} or row["id"] in seen:raise ValueError("invalid multibound")
        seen.add(row["id"]);box=bounds(row);room=row["room"]
        if room not in rooms or not all(contains(rooms[room],p) for p in box):raise ValueError("multibound outside room")
        groups[row["id"]]=box
    planes=[]
    for row in spec.get("occluders",[]):
        if set(row)!={"id","room","corners"} or row["id"] in seen:raise ValueError("invalid occluder")
        seen.add(row["id"]);room=row["room"];corners=[point(p) for p in row["corners"]]
        if room not in rooms or len(corners)!=4 or len(set(corners))!=4 or not all(contains(rooms[room],p) for p in corners):raise ValueError("invalid occluder corners")
        fixed=[i for i in range(3) if max(p[i] for p in corners)-min(p[i] for p in corners)<1e-6]
        if len(fixed)!=1:raise ValueError("axis-aligned occluder required")
        axis=fixed[0];axes=[i for i in range(3) if i!=axis]
        lo=[min(p[i] for p in corners) for i in range(3)];hi=[max(p[i] for p in corners) for i in range(3)]
        if {(p[axes[0]],p[axes[1]]) for p in corners}!={(x,y) for x in (lo[axes[0]],hi[axes[0]]) for y in (lo[axes[1]],hi[axes[1]])}:raise ValueError("rectangular occluder required")
        for portal in portals:
            if room not in portal["rooms"]:continue
            pc=portal["corners"]
            if all(abs(p[axis]-lo[axis])<=1e-6 for p in pc) and all(max(min(p[i] for p in pc),lo[i])<min(max(p[i] for p in pc),hi[i]) for i in axes):
                issues.append({"code":"occluder-overlaps-portal","occluder":row["id"],"portal":portal["id"]})
        planes.append({"id":row["id"],"corners":ordered(corners)})
    assignments={}
    for obj in objects:
        box=bounds(obj);matches=[id for id,b in groups.items() if all(contains(b,p,tol=0) for p in box)]
        if len(matches)==1:assignments[obj["id"]]=matches[0]
        elif len(matches)>1:issues.append({"code":"ambiguous-multibound","object":obj["id"],"matches":matches})
    return {"multibounds":len(groups),"occluders":planes,"assignments":assignments,"issues":issues,
            "scope":"portable geometry review; no native occlusion records or runtime culling"}
