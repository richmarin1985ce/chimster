"""Portable cloudbank geometry; native shader and NIF export require a verified template."""
from math import isfinite,ceil

def regenerate(bounds,*,height,texture_period,padding=0,max_segments=128):
    """Bounds in world units (xmin,ymin,xmax,ymax); texture period in world units.
    Generate a tiled UV plane with consistent texel density and upward winding.
    """
    x0,y0,x1,y1=bounds
    if not all(isfinite(v) for v in (*bounds,height,texture_period,padding)) or x1<=x0 or y1<=y0 or texture_period<=0 or padding<0:raise ValueError("Invalid cloudbank dimensions")
    if type(max_segments)!=int or not 1<=max_segments<=512:raise ValueError("Invalid segment limit")
    x0-=padding;y0-=padding;x1+=padding;y1+=padding
    nx=min(max_segments,max(1,ceil((x1-x0)/texture_period)))
    ny=min(max_segments,max(1,ceil((y1-y0)/texture_period)))
    vertices=[];uv=[];triangles=[]
    for j in range(ny+1):
        y=y0+(y1-y0)*j/ny
        for i in range(nx+1):
            x=x0+(x1-x0)*i/nx
            vertices.append((x,y,height))
            uv.append((x/texture_period,y/texture_period))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;b=a+1;c=a+nx+1;d=c+1
            triangles.extend(((a,b,d),(a,d,c)))
    return {"vertices":vertices,"uv":uv,"triangles":triangles,
            "normals":[(0,0,1)]*len(vertices),"bounds":(x0,y0,x1,y1),
            "native_encoded":False,"requires_verified_cloud_material":True}
