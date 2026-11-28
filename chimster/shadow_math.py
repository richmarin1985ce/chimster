"""Stable directional shadow anchor in light-space texel units."""
from math import sqrt
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(v):
    length=sqrt(dot(v,v))
    if not length:raise ValueError("Zero direction")
    return tuple(x/length for x in v)
def snap_center(center,direction,extent,resolution):
    if not resolution:return tuple(center)
    n=unit(direction)
    ref=(0,0,1) if abs(n[2])<.99 else (0,1,0)
    r=unit(cross(n,ref));u=cross(r,n)
    texel=2*extent/resolution
    dr=round(dot(center,r)/texel)*texel-dot(center,r)
    du=round(dot(center,u)/texel)*texel-dot(center,u)
    return tuple(center[i]+dr*r[i]+du*u[i] for i in range(3))
