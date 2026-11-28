"""Generate tangent frames for preview geometry without changing source meshes."""
from math import sqrt
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def unit(a):
    n=sqrt(dot(a,a))
    return tuple(x/n for x in a) if n>1e-12 else None

def tangents(mesh,raw):
    ts=[[0.,0.,0.] for _ in mesh.vertices];bs=[[0.,0.,0.] for _ in mesh.vertices]
    for tri,_ in mesh.faces:
        i,j,k=tri;a,b,c=(mesh.vertices[x] for x in tri)
        u,v,w=(mesh.uv[x] for x in tri)
        e,f=sub(b,a),sub(c,a);du,dv=sub(v,u),sub(w,u)
        det=du[0]*dv[1]-du[1]*dv[0]
        if abs(det)<1e-12:continue
        t=tuple((e[x]*dv[1]-f[x]*du[1])/det for x in range(3))
        bit=tuple((f[x]*du[0]-e[x]*dv[0])/det for x in range(3))
        for a in tri:
            for x in range(3):ts[a][x]+=t[x];bs[a][x]+=bit[x]
    result=[]
    for i,t in enumerate(ts):
        n=tuple(raw[i*8+3:i*8+6]);projected=tuple(t[j]-n[j]*dot(n,t) for j in range(3))
        u=unit(projected)
        if u is None:u=unit(cross((0,0,1) if abs(n[2])<.9 else (0,1,0),n)) or (1.,0.,0.)
        sign=-1. if dot(cross(n,u),bs[i])<0 else 1.
        result.append((*u,sign))
    return result

def normal_pixels(image,directx,strength):
    """Convert DirectX Y and scale XY in RGBA8; reconstruct positive Z."""
    from .gpu_viewport import ImageMap
    image.validate();out=bytearray(image.rgba)
    for i in range(0,len(out),4):
        x=(out[i]/255*2-1)*strength;y=(out[i+1]/255*2-1)*strength*(-1 if directx else 1)
        z=sqrt(max(0.,1-x*x-y*y))
        n=unit((x,y,z)) or (0,0,1)
        out[i:i+3]=bytes(round((v*.5+.5)*255) for v in n)
    return ImageMap(image.width,image.height,bytes(out))
