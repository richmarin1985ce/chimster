"""Bounded mesh topology and UV operations; no implicit cross-seam welding."""
from copy import deepcopy
from math import isfinite, dist
from collections import defaultdict
from .flora import Mesh,cross

def compact(m):
    used=sorted({v for t,_ in m.faces for v in t}); remap={v:i for i,v in enumerate(used)}
    return Mesh([m.vertices[i] for i in used],[m.uv[i] for i in used],
                [(tuple(remap[v] for v in t),mat) for t,mat in m.faces])

def area(m,t):
    a,b,c=[m.vertices[i] for i in t]
    return cross(tuple(y-x for x,y in zip(a,b)),tuple(y-x for x,y in zip(a,c)))

def extrude(mesh,ids,delta):
    if len(delta)!=3 or not all(isfinite(x) for x in delta) or not any(delta):
        raise ValueError("Nonzero finite extrusion vector required")
    edges=defaultdict(list);global_counts=defaultdict(int)
    for i,(t,mat) in enumerate(mesh.faces):
        for a,b in zip(t,t[1:]+t[:1]):
            key=tuple(sorted((a,b)));global_counts[key]+=1
            if i in ids:edges[key].append((a,b,mat))
    if any(len(v)>2 or global_counts[k]>2 or
           (len(v)==2 and v[0][:2]!=v[1][:2][::-1]) for k,v in edges.items()):
        raise ValueError("Extrusion requires consistently wound manifold selected edges")
    boundary=[v[0] for v in edges.values() if len(v)==1]
    if not boundary:raise ValueError("Selection needs a boundary")
    incidence=defaultdict(int)
    for a,b,_ in boundary:incidence[a]+=1;incidence[b]+=1
    if any(n!=2 for n in incidence.values()):raise ValueError("Ambiguous boundary junction")
    m=deepcopy(mesh);used=sorted({v for i in ids for v in m.faces[i][0]});mapping={}
    for v in used:
        mapping[v]=len(m.vertices);m.vertices.append(tuple(x+y for x,y in zip(mesh.vertices[v],delta)));m.uv.append(mesh.uv[v])
    m.faces=[(tuple(mapping[v] for v in t),mat) if i in ids else (t,mat) for i,(t,mat) in enumerate(m.faces)]
    for a,b,mat in boundary:
        # Keep topology joined. Side UVs inherit the cap's UVs; unwrap separately.
        m.faces.extend([((a,b,mapping[b]),mat),((a,mapping[b],mapping[a]),mat)])
    if any(not any(area(m,t)) for t,_ in m.faces[len(mesh.faces):]):
        raise ValueError("Extrusion creates a collapsed side")
    return compact(m),sorted(ids)

def weld(mesh,ids,tolerance):
    if len(ids)<2 or not isfinite(tolerance) or not 0<=tolerance<=1e6:raise ValueError("Select at least two vertices and a valid tolerance")
    target=min(ids);p=mesh.vertices[target];uv=mesh.uv[target]
    if any(dist(p,mesh.vertices[i])>tolerance or mesh.uv[i]!=uv for i in ids):
        raise ValueError("Vertices must lie within tolerance of target and share exact UVs")
    memberships=defaultdict(set)
    for t,mat in mesh.faces:
        for v in t:
            if v in ids:memberships[v].add(mat)
    if any(memberships[i]!=memberships[target] for i in ids):
        raise ValueError("Welding across material boundaries is disabled")
    m=deepcopy(mesh);faces=[];seen=set()
    for t,mat in m.faces:
        u=tuple(target if v in ids else v for v in t)
        if len(set(u))<3:continue
        key=tuple(sorted(u))
        if key in seen:raise ValueError("Weld would create duplicate faces")
        seen.add(key)
        if u!=t and not any(area(m,u)):raise ValueError("Weld collapses a face")
        faces.append((u,mat))
    m.faces=faces
    return compact(m)

def planar_uv(mesh,ids,plane):
    axes={"XY":(0,1),"XZ":(0,2),"YZ":(1,2)}
    if plane not in axes:raise ValueError("Choose XY, XZ or YZ")
    a,b=axes[plane];used={v for i in ids for v in mesh.faces[i][0]}
    lo=[min(mesh.vertices[v][k] for v in used) for k in (a,b)]
    hi=[max(mesh.vertices[v][k] for v in used) for k in (a,b)]
    if min(h-l for h,l in zip(hi,lo))<=1e-12:raise ValueError("Projection has zero extent")
    other={v for i,(t,_) in enumerate(mesh.faces) if i not in ids for v in t}
    m=deepcopy(mesh);mapping={}
    for v in sorted(used):
        i=v
        if v in other:
            i=len(m.vertices);m.vertices.append(mesh.vertices[v]);m.uv.append(mesh.uv[v])
        mapping[v]=i;m.uv[i]=tuple((mesh.vertices[v][k]-lo[j])/(hi[j]-lo[j]) for j,k in enumerate((a,b)))
    m.faces=[(tuple(mapping[v] for v in t),mat) if i in ids else (t,mat) for i,(t,mat) in enumerate(mesh.faces)]
    return m
