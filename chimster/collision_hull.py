"""Bounded convex polyhedron reconstruction from native collision core points."""
from itertools import combinations
import math


def hull(points):
    pts=sorted(set(tuple(float(x) for x in p) for p in points))
    if not 4<=len(pts)<=64 or any(len(p)!=3 or not all(math.isfinite(x) and abs(x)<=1e7 for x in p) for p in pts):
        raise ValueError("invalid convex core points")
    extent=max(max(p[k] for p in pts)-min(p[k] for p in pts) for k in range(3))
    eps=max(extent*1e-8,1e-10)
    def sub(a,b):return tuple(x-y for x,y in zip(a,b))
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    def dot(a,b):return sum(x*y for x,y in zip(a,b))
    faces={}
    for i,j,k in combinations(range(len(pts)),3):
        a,b,c=pts[i],pts[j],pts[k]
        normal=cross(sub(b,a),sub(c,a));length=math.hypot(*normal)
        if length<=eps*eps:continue
        n=tuple(v/length for v in normal)
        dist=[dot(n,sub(p,a)) for p in pts]
        if max(dist)>eps and min(dist)<-eps:continue
        if max(dist)<=eps and min(dist)>=-eps:continue
        if max(dist)>eps:n=tuple(-v for v in n)
        face=tuple(t for t,d in enumerate(dist) if abs(d)<=eps)
        faces.setdefault(face,n)
    if len(faces)<4:raise ValueError("degenerate convex core")
    tris=[]
    for face,n in sorted(faces.items()):
        axis=max(range(3),key=lambda k:abs(n[k]));u,v=[k for k in range(3) if k!=axis]
        seq=sorted(face,key=lambda i:(pts[i][u],pts[i][v]))
        def turn(a,b,c):
            x,y,z=pts[a],pts[b],pts[c]
            return (y[u]-x[u])*(z[v]-x[v])-(y[v]-x[v])*(z[u]-x[u])
        def chain(items):
            out=[]
            for i in items:
                while len(out)>=2 and turn(out[-2],out[-1],i)<=eps*eps:out.pop()
                out.append(i)
            return out
        ring=chain(seq)[:-1]+chain(reversed(seq))[:-1]
        if len(ring)<3:raise ValueError("degenerate convex face")
        if dot(cross(sub(pts[ring[1]],pts[ring[0]]),sub(pts[ring[2]],pts[ring[0]])),n)<0:ring.reverse()
        tris.extend((ring[0],ring[i],ring[i+1]) for i in range(1,len(ring)-1))
    edges={}
    for t in tris:
        for a,b in zip(t,t[1:]+t[:1]):edges.setdefault(tuple(sorted((a,b))),[]).append((a,b))
    if any(len(e)!=2 or e[0]!=e[1][::-1] for e in edges.values()):raise ValueError("nonmanifold convex reconstruction")
    return pts,tris
