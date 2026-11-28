"""Portable recursive portal visibility; conservative fallback on traversal budget."""
from math import sqrt
from .interior_layout import validate,point,bounds,contains,candidates

def dot(a,b):return sum(x*y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def clip(poly,n,d,eps=1e-7):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        u,v=dot(n,a)+d,dot(n,b)+d
        inside=u>=-eps;other=v>=-eps
        if inside:out.append(a)
        if inside!=other:
            t=(u+eps)/(u-v)
            out.append(tuple(x+t*(y-x) for x,y in zip(a,b)))
    return out

def ordered(corners):
    from math import atan2
    c=tuple(sum(p[i] for p in corners)/4 for i in range(3))
    axes=[i for i in range(3) if max(p[i] for p in corners)-min(p[i] for p in corners)>1e-6]
    return sorted(corners,key=lambda p:atan2(p[axes[1]]-c[axes[1]],p[axes[0]]-c[axes[0]]))

def visible(layout,room,eye,planes=(),closed=(),budget=4096):
    """Planes use inward normals: dot(n,p)+d >= 0. Never cull on budget exhaustion."""
    report=validate(layout)
    if not report["valid"]:raise ValueError("Invalid layout")
    eye=point(eye);rooms={r["id"]:bounds(r) for r in layout["rooms"]}
    if room not in rooms or not contains(rooms[room],eye):raise ValueError("Camera outside room")
    if not 1<=budget<=100000:raise ValueError("Invalid budget")
    from math import isfinite
    initial=[]
    for n,d in planes:
        n=point(n);length=sqrt(dot(n,n))
        if length<1e-12 or not isfinite(d):raise ValueError("Invalid frustum plane")
        initial.append((tuple(v/length for v in n),d/length))
    blocked=set(closed);fallback=candidates(layout,room,blocked)["visible_candidates"]
    graph={r:[] for r in rooms}
    for p in layout.get("portals",[]):
        if p["id"] in blocked:continue
        a,b=p["rooms"];poly=ordered([point(c) for c in p["corners"]])
        graph[a].append((b,poly));graph[b].append((a,poly))
    stack=[(room,tuple(initial),frozenset((room,)))];seen={room};steps=0
    while stack:
        current,frustum,path=stack.pop()
        for target,poly in graph[current]:
            if target in path:continue
            steps+=1
            if steps>budget:return {"visible_candidates":fallback,"fallback":True,"steps":steps}
            for n,d in frustum:
                poly=clip(poly,n,d)
                if not poly:break
            if not poly:continue
            center=tuple(sum(p[i] for p in poly)/len(poly) for i in range(3))
            extra=[]
            for a,b in zip(poly,poly[1:]+poly[:1]):
                n=cross(sub(a,eye),sub(b,eye));length=sqrt(dot(n,n))
                if length<1e-10:continue
                n=tuple(v/length for v in n)
                if dot(n,sub(center,eye))<0:n=tuple(-v for v in n)
                extra.append((n,-dot(n,eye)))
            seen.add(target)
            stack.append((target,frustum+tuple(extra),path|{target}))
    return {"visible_candidates":sorted(seen),"fallback":False,"steps":steps}
