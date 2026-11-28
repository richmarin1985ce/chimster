"""Pointer-independent freehand samples and editable outline conversion."""
from dataclasses import dataclass
from math import hypot,isfinite
from .font_project import nodes

@dataclass(frozen=True)
class Sample:
    x: float
    y: float
    pressure: float | None = None

def outline(samples,width=40,smoothing=1):
    """Convert a simple open stroke to a variable-width closed polygon.
    Missing pressure means nominal width; tight folds may need manual editing.
    """
    if not 5<=width<=200 or smoothing not in (0,1,2,3):
        raise ValueError("Invalid stroke settings")
    pts=[]
    for s in samples:
        if not all(isfinite(v) for v in (s.x,s.y)) or not -800<=s.x<=1800 or not -800<=s.y<=1800:
            raise ValueError("Invalid pointer coordinates")
        if s.pressure is not None and (not isfinite(s.pressure) or not 0<=s.pressure<=1):
            raise ValueError("Invalid pressure")
        if not pts or hypot(s.x-pts[-1].x,s.y-pts[-1].y)>=3:pts.append(s)
        if len(pts)>1000:raise ValueError("Stroke too long; split into segments")
    if len(pts)<2:raise ValueError("Draw a longer stroke")
    for _ in range(smoothing):
        pts=[pts[0]]+[Sample((a.x+2*b.x+c.x)/4,(a.y+2*b.y+c.y)/4,b.pressure) for a,b,c in zip(pts,pts[1:],pts[2:])]+[pts[-1]]
    left=[];right=[]
    for i,s in enumerate(pts):
        a,b=pts[max(0,i-1)],pts[min(len(pts)-1,i+1)]
        dx,dy=b.x-a.x,b.y-a.y
        length=hypot(dx,dy)
        if length<1e-6:continue
        radius=width/2*(1 if s.pressure is None else .2+.8*s.pressure)
        nx,ny=-dy/length*radius,dx/length*radius
        left.append((round(s.x+nx),round(s.y+ny),True))
        right.append((round(s.x-nx),round(s.y-ny),True))
    return nodes(left+right[::-1])
