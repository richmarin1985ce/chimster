"""Engine-independent visibility geometry. Angles are radians; axes explicit."""
from math import sqrt,isfinite
from .interior_layout import point
from .portal_clip import dot,sub,cross

class OrientedBox:
    def __init__(self,center,half_extents,axes):
        self.center=point(center);self.half=point(half_extents)
        self.axes=tuple(point(a) for a in axes)
        if len(self.axes)!=3 or any(v<=0 for v in self.half):raise ValueError("Invalid box")
        for i,a in enumerate(self.axes):
            for j,b in enumerate(self.axes):
                if abs(dot(a,b)-(1 if i==j else 0))>1e-6:raise ValueError("Axes must be orthonormal")
    def contains(self,p,tolerance=1e-6):
        delta=sub(point(p),self.center)
        return all(abs(dot(delta,a))<=h+tolerance for a,h in zip(self.axes,self.half))
    def corners(self):
        from itertools import product
        return tuple(tuple(self.center[i]+sum(s*h*a[i] for s,h,a in zip(signs,self.half,self.axes)) for i in range(3)) for signs in product((-1,1),repeat=3))
    def plane_interval(self,normal,offset):
        n=point(normal)
        if dot(n,n)<1e-20 or not isfinite(offset):raise ValueError("Invalid plane")
        center=dot(n,self.center)+offset
        radius=sum(h*abs(dot(n,a)) for h,a in zip(self.half,self.axes))
        return center-radius,center+radius
    def outside(self,planes,tolerance=1e-6):
        return any(self.plane_interval(n,d)[1]<-tolerance*sqrt(dot(n,n)) for n,d in planes)
    def aabb(self):
        radius=tuple(sum(h*abs(a[i]) for h,a in zip(self.half,self.axes)) for i in range(3))
        return tuple(c-r for c,r in zip(self.center,radius)),tuple(c+r for c,r in zip(self.center,radius))

def portal_planes(eye,corners):
    """Ordered convex aperture; return inward planes through the eye.
    Degenerate edge planes are omitted conservatively.
    """
    eye=point(eye);poly=[point(p) for p in corners]
    if not 3<=len(poly)<=64:raise ValueError("Invalid aperture")
    center=tuple(sum(p[i] for p in poly)/len(poly) for i in range(3))
    planes=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        n=cross(sub(a,eye),sub(b,eye));length=sqrt(dot(n,n))
        if length<1e-10:continue
        n=tuple(v/length for v in n)
        if dot(n,sub(center,eye))<0:n=tuple(-v for v in n)
        d=-dot(n,eye)
        if any(dot(n,p)+d < -1e-6 for p in poly):return ()
        planes.append((n,d))
    return tuple(planes)
