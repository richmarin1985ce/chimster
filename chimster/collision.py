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

def compound_boxes(mesh):
    """One conservative AABB per vertex-connected component, preserving empty gaps.
    Disconnected UV seams can split components; this is not a convex decomposition."""
    validate_mesh(mesh)
    parent=list(range(len(mesh.vertices)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=parent[i]
        return i
    used=set()
    for tri,_ in mesh.faces:
        a,b,c=tri;used.update(tri)
        parent[find(b)]=find(a);parent[find(c)]=find(a)
    groups={}
    for i in sorted(used):groups.setdefault(find(i),[]).append(mesh.vertices[i])
    result=[]
    for verts in groups.values():
        lo=tuple(min(p[k] for p in verts) for k in range(3));hi=tuple(max(p[k] for p in verts) for k in range(3))
        if any(a>=b for a,b in zip(lo,hi)):raise ValueError("flat component; supply a solid proxy mesh")
        result.append((lo,hi))
    return result

def export_compound(mesh,output):
    boxes=compound_boxes(mesh)
    p=Path(output);p.mkdir(parents=True,exist_ok=False)
    from .flora import write_obj
    merged=Mesh()
    for n,(lo,hi) in enumerate(boxes):
        m=proxy(Mesh([lo,hi, (lo[0],hi[1],lo[2])],[(0,0)]*3,[((0,1,2),"proxy")]))
        base=len(merged.vertices);merged.vertices.extend(m.vertices);merged.uv.extend(m.uv)
        merged.faces.extend((tuple(base+j for j in t),f"collision_{n}") for t,_ in m.faces)
    write_obj(merged,p/"collision.obj")
    info={"kind":"compound_aabb","boxes":[{"min":lo,"max":hi} for lo,hi in boxes],"status":"portable proxy only; native compound collision not implemented"}
    (p/"collision.json").write_text(json.dumps(info,indent=2),encoding="utf-8")
    return info
