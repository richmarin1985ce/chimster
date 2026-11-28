"""Preview geometry only. No default unverified Bethesda quaternion convention."""
from math import hypot,isfinite,cos,sin
from .interior_layout import point
from .visibility_geometry import OrientedBox
from .portal_clip import dot

def quaternion_axes(raw,order):
    if order not in ("xyzw","wxyz"):raise ValueError("Explicit quaternion order required")
    if len(raw)!=4 or not all(isfinite(v) for v in raw):raise ValueError("Invalid quaternion")
    x,y,z,w=raw if order=="xyzw" else (*raw[1:],raw[0])
    length=hypot(x,y,z,w)
    if length<1e-12:raise ValueError("Zero quaternion")
    x,y,z,w=(v/length for v in (x,y,z,w))
    return ((1-2*(y*y+z*z),2*(x*y+w*z),2*(x*z-w*y)),
            (2*(x*y-w*z),1-2*(x*x+z*z),2*(y*z+w*x)),
            (2*(x*z+w*y),2*(y*z-w*x),1-2*(x*x+y*y)))

class Mapping:
    def __init__(self,axes,scale,origin=(0,0,0)):
        self.axes=OrientedBox((0,0,0),(1,1,1),axes).axes
        if not isfinite(scale) or scale<=0:raise ValueError("Invalid scale")
        self.scale=scale;self.origin=point(origin)
    def direction(self,p):
        return tuple(sum(p[j]*self.axes[j][i] for j in range(3)) for i in range(3))
    def position(self,p):
        return tuple(a+self.scale*b for a,b in zip(self.origin,self.direction(point(p))))

def rectangle(record,mapping,*,order,plane,dimension_factor):
    if plane not in ("xy","xz","yz") or dimension_factor not in (.5,1):raise ValueError("Explicit plane and extent convention required")
    a,b=record["dimensions"]
    if not all(isfinite(v) and v>0 for v in (a,b)):raise ValueError("Invalid rectangle")
    axes=quaternion_axes(record["quaternion_raw"],order)
    u,v=[axes["xyz".index(c)] for c in plane]
    center=point(record["position"])
    return tuple(mapping.position(tuple(center[i]+dimension_factor*(s*a*u[i]+t*b*v[i]) for i in range(3))) for s,t in ((-1,-1),(1,-1),(1,1),(-1,1)))

def box(center,half_extents,axes,mapping):
    return OrientedBox(mapping.position(center),tuple(v*mapping.scale for v in half_extents),tuple(mapping.direction(a) for a in axes))

def membership(objects,rooms):
    """Only assign objects whose entire bounding box lies in exactly one room."""
    result={}
    for key,volume in objects.items():
        corners=volume.corners()
        matches=[room for room,b in rooms.items() if all(b.contains(p, tolerance=0) for p in corners)]
        if len(matches)==1:result[key]=matches[0]
    return result
