"""Local terrain tools for staged worldspace creation."""
from math import isfinite,hypot,floor
from .worldspace import Terrain

def sample_height(t,x_m,y_m):
    """Bilinear sample using the same south-to-north grid as the native writer."""
    t.validate()
    if not all(isfinite(v) for v in (x_m,y_m)):raise ValueError("invalid position")
    x,y=x_m/t.spacing_m,y_m/t.spacing_m;n=len(t.heights)-1
    if not 0<=x<=n or not 0<=y<=n:raise ValueError("position outside terrain")
    i,j=min(n-1,floor(x)),min(n-1,floor(y));a,b=x-i,y-j
    r=t.heights
    return (1-b)*((1-a)*r[j][i]+a*r[j][i+1])+b*((1-a)*r[j+1][i]+a*r[j+1][i+1])

def brush(t,x,y,radius,mode,strength=1.,target=None):
    t.validate()
    if mode not in {"smooth","flatten"} or not all(isfinite(v) for v in (x,y,radius,strength)) or radius<=0 or not 0<=strength<=1:raise ValueError("invalid brush")
    if mode=="flatten" and (target is None or not isfinite(target)):raise ValueError("flatten target required")
    n=len(t.heights);rows=[]
    for j,row in enumerate(t.heights):
        result=[]
        for i,z in enumerate(row):
            weight=strength*max(0.,1-hypot(i-x,j-y)/radius)**2
            if weight:
                if mode=="smooth":
                    points=[t.heights[b][a] for b in range(max(0,j-1),min(n,j+2)) for a in range(max(0,i-1),min(n,i+2))]
                    goal=sum(points)/len(points)
                else:goal=target
                z+=(goal-z)*weight
            result.append(z)
        rows.append(tuple(result))
    return Terrain(tuple(rows),t.spacing_m,t.datum_m).validate()

def snap_placements(t,placements):
    """Explicit opt-in placement height and offset; do not move other objects."""
    result=[]
    for item in placements:
        p=dict(item)
        if p.pop("snap_to_ground",False):
            if "z_m" in p:raise ValueError("choose explicit z_m or ground snapping")
            offset=p.pop("height_offset_m",0.)
            if not isfinite(offset):raise ValueError("invalid height offset")
            p["z_m"]=sample_height(t,p["x_m"],p["y_m"])+offset
        elif "height_offset_m" in p:raise ValueError("height_offset_m requires ground snapping")
        result.append(p)
    return result
