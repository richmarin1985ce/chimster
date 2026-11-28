"""Portable navigation area classification and weighted routes."""
import math
from collections import Counter
from .navmesh import num,point,topology

def classify(mesh,policy=None):
    policy=policy or {}
    if set(policy)-{"ramp_degrees","steep_degrees","zones","costs"}:raise ValueError("unknown area policy")
    ramp=num(policy.get("ramp_degrees",5),0,89)
    steep=num(policy.get("steep_degrees",25),ramp,89.9)
    costs={"ground":1.,"ramp":1.25,"steep":2.,"stair":1.5,**policy.get("costs",{})}
    if any(not isinstance(k,str) or not k or len(k)>64 for k in costs):raise ValueError("invalid area name")
    costs={k:num(v,.01,10000) for k,v in costs.items()}
    zones=[]
    for z in policy.get("zones",[]):
        if set(z)!={"min","max","area"} or z["area"] not in costs:raise ValueError("invalid area zone")
        lo,hi=point(z["min"]),point(z["max"])
        if any(a>=b for a,b in zip(lo,hi)):raise ValueError("invalid area bounds")
        zones.append((lo,hi,z["area"]))
    vs=mesh["vertices"];ts=mesh["triangles"];topology(vs,ts)
    if len(zones)*len(ts)>10000000:raise ValueError("area classification work limit")
    stairs={i for l in mesh.get("links",[]) if l.get("kind")=="step" for i in (l["from"],l["to"])}
    labels=[];mixed=0
    for i,t in enumerate(ts):
        a,b,c=[vs[j] for j in t]
        u=[b[j]-a[j] for j in range(3)];v=[c[j]-a[j] for j in range(3)]
        n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        angle=math.degrees(math.atan2(math.hypot(n[0],n[1]),n[2]))
        label="stair" if i in stairs else "steep" if angle>=steep else "ramp" if angle>=ramp else "ground"
        for lo,hi,area in zones:
            if all(all(lo[k]<=p[k]<=hi[k] for k in range(3)) for p in (a,b,c)):label=area
            elif all(max(p[k] for p in (a,b,c))>=lo[k] and min(p[k] for p in (a,b,c))<=hi[k] for k in range(3)):mixed+=1
        labels.append(label)
    return {**mesh,"triangle_areas":labels,"area_costs":costs,"area_report":{"counts":dict(Counter(labels)),"partial_zone_overlaps":mixed}}

def paint(mesh,indices,area):
    if area not in mesh.get("area_costs",{}):raise ValueError("unknown area")
    labels=list(mesh["triangle_areas"])
    if len(labels)!=len(mesh["triangles"]):raise ValueError("area metadata length")
    for i in set(indices):
        if type(i) is not int or not 0<=i<len(labels):raise ValueError("invalid triangle")
        labels[i]=area
    return {**mesh,"triangle_areas":labels,"area_report":{**mesh.get("area_report",{}),"counts":dict(Counter(labels))}}
