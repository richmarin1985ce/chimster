"""In-process paired diffuse/normal atlases for opaque, non-tiling object LOD."""
from .atlas import Tile,pack,remap_uv
from .lod_dds import decode
from .flora import Mesh
from math import ceil,sqrt
from hashlib import sha256

def resize(image,size):
    w,h,rgba=image
    # Bounded box sampling; preserve the same layout for diffuse and normal.
    out=bytearray(size*size*4)
    for y in range(size):
        a,b=y*h//size,max(y*h//size+1,(y+1)*h//size)
        for x in range(size):
            c,d=x*w//size,max(x*w//size+1,(x+1)*w//size)
            n=(b-a)*(d-c);total=[0]*4
            for j in range(a,b):
                for i in range(c,d):
                    k=(j*w+i)*4
                    for t in range(4):total[t]+=rgba[k+t]
            out[(y*size+x)*4:(y*size+x+1)*4]=bytes(round(v/n) for v in total)
    return bytes(out)

def build(groups,assets,size=128,maximum=2048):
    """Return atlas mesh, DDS input images, provenance and skipped groups.
    UVs outside [0,1], alpha textures and unsupported textures stay separate.
    """
    if size not in (32,64,128,256) or maximum not in (256,512,1024,2048):raise ValueError("Invalid atlas size")
    eligible=[];remaining=[];diff=[];norm=[];hashes={};issues=[]
    capacity=(maximum//(size+8))**2
    for mesh,d,n in groups:
        try:
            if len(eligible)>=capacity:raise ValueError("Atlas capacity reached")
            if any(not 0<=u<=1 or not 0<=v<=1 for u,v in mesh.uv):raise ValueError("Tiling UVs")
            a,b=assets.get(d),assets.get(n)
            di,ni=decode(a),decode(b)
            if any(v!=255 for v in di[2][3::4]):raise ValueError("Nonopaque diffuse texture")
            if sum(len(m.vertices) for m,_,_ in eligible)+len(mesh.vertices)>65535 or sum(len(m.faces) for m,_,_ in eligible)+len(mesh.faces)>65535:raise ValueError("Atlas geometry budget")
            key=str(len(eligible));diff.append(Tile(key,size,size,resize(di,size)));norm.append(Tile(key,size,size,resize(ni,size)))
            hashes[d]=sha256(a).hexdigest();hashes[n]=sha256(b).hexdigest()
            eligible.append((mesh,d,n))
        except (ValueError,OSError,TypeError) as exc:
            remaining.append((mesh,d,n));issues.append({"diffuse":d,"reason":str(exc)})
    if not eligible:return None,remaining,issues
    side=256
    while (side//(size+8))**2<len(eligible):side*=2
    rgba,layout=pack(diff,side,side,4);normal,other=pack(norm,side,side,4)
    if other!=layout:raise ValueError("Paired atlas layout mismatch")
    merged=Mesh()
    for i,(mesh,d,n) in enumerate(eligible):
        offset=len(merged.vertices);merged.vertices.extend(mesh.vertices)
        rect=layout[str(i)]
        # NIF writer flips V; atlas image has top-left origin.
        for u,v in mesh.uv:
            a,b=remap_uv(u,1-v,rect);merged.uv.append((a,1-b))
        merged.faces.extend((tuple(j+offset for j in f),"lod_atlas") for f,_ in mesh.faces)
    return {"mesh":merged,"diffuse":rgba,"normal":normal,"size":side,"source_hashes":hashes,"groups":len(eligible)},remaining,issues
