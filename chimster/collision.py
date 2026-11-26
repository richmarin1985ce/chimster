"""Portable collision bounds, mesh proxies and ray tests. Not Havok serialization."""
from .flora import Mesh
from .lod import validate_mesh
from math import isfinite
from pathlib import Path
import json
def box(mesh):
    validate_mesh(mesh)
    lo=tuple(min(p[k] for p in mesh.vertices) for k in range(3));hi=tuple(max(p[k] for p in mesh.vertices) for k in range(3))
    if any(a>=b for a,b in zip(lo,hi)):raise ValueError("collision box requires nonzero extent")
    return lo,hi
def proxy(mesh):
    lo,hi=box(mesh)
    v=[(x,y,z) for z in (lo[2],hi[2]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])]
    t=[(0,2,1),(1,2,3),(4,5,6),(5,7,6),(0,1,4),(1,5,4),(2,6,3),(3,6,7),(0,4,2),(2,4,6),(1,3,5),(3,7,5)]
    return Mesh(v,[(0,0)]*8,[(f,"collision") for f in t])
def ray_box(origin,direction,lo,hi):
    if not all(isfinite(v) for p in (origin,direction,lo,hi) for v in p) or not any(direction):raise ValueError("invalid ray")
    near,far=0.,float("inf")
    for o,d,a,b in zip(origin,direction,lo,hi):
        if d==0:
            if not a<=o<=b:return None
        else:
            t,u=sorted(((a-o)/d,(b-o)/d));near=max(near,t);far=min(far,u)
            if near>far:return None
    return near
def export_box(mesh,output):
    lo,hi=box(mesh)
    from .flora import write_obj
    p=Path(output);p.mkdir(parents=True,exist_ok=False)
    write_obj(proxy(mesh),p/"collision.obj")
    info={"kind":"aabb","min":lo,"max":hi,"status":"portable collision proxy only; not native Havok"}
    (p/"collision.json").write_text(json.dumps(info,indent=2),encoding="utf-8")
    return info
