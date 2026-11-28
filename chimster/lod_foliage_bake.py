"""Bounded CPU foliage impostor baking with source DDS, UVs and alpha testing."""
from math import sin,cos,pi,floor,ceil,sqrt,isfinite
from hashlib import sha256
from .lod import validate_mesh
from .flora import Mesh,cross
from .atlas import Tile,pack,remap_uv
from .lod_dds import decode

def bake(groups,assets,size=128,angle=0):
    if size not in (32,64,128,256) or not isfinite(angle):raise ValueError("Invalid foliage bake dimensions")
    if not 1<=len(groups)<=128:raise ValueError("Foliage material budget")
    c,s=cos(angle),sin(angle)
    projected=[];cache={};hashes={};count=0
    for mesh,diffuse,normal,cutout in groups:
        validate_mesh(mesh);count+=len(mesh.faces)
        if count>100000:raise ValueError("Foliage triangle budget")
        if diffuse not in cache:
            raw=assets.get(diffuse);image=decode(raw)
            if sum(w*h for w,h,_ in cache.values())+image[0]*image[1]>16777216:raise ValueError("Foliage texture budget")
            cache[diffuse]=image;hashes[diffuse]=sha256(raw).hexdigest()
        p=[(c*x+s*y,z,-s*x+c*y) for x,y,z in mesh.vertices]
        projected.append((mesh,p,cache[diffuse],cutout))
    lo=min(v[0] for _,p,_,_ in projected for v in p);hi=max(v[0] for _,p,_,_ in projected for v in p)
    bottom=min(v[1] for _,p,_,_ in projected for v in p);top=max(v[1] for _,p,_,_ in projected for v in p)
    # Symmetric horizontal extent retains the tree's placement origin.
    half=max(abs(lo),abs(hi),1e-6);height=top-bottom
    if height<=1e-6:raise ValueError("Foliage has no vertical extent")
    span=max(2*half,height)*size/(size-4);mid=(bottom+top)/2;scale=size/span
    depth=[float("-inf")]*(size*size);pixels=bytearray(size*size*4);normals=bytearray(bytes((128,128,255,255))*(size*size))
    operations=0
    for mesh,points,(tw,th,tex),cutout in projected:
        pts=[(x*scale+size/2,(mid-y)*scale+size/2,z) for x,y,z in points]
        for tri,_ in mesh.faces:
            a,b,d=[pts[i] for i in tri]
            den=(b[1]-d[1])*(a[0]-d[0])+(d[0]-b[0])*(a[1]-d[1])
            if abs(den)<1e-9:continue
            x0=max(0,floor(min(a[0],b[0],d[0])));x1=min(size,ceil(max(a[0],b[0],d[0]))+1)
            y0=max(0,floor(min(a[1],b[1],d[1])));y1=min(size,ceil(max(a[1],b[1],d[1]))+1)
            operations+=max(0,x1-x0)*max(0,y1-y0)
            if operations>16000000:raise ValueError("Foliage raster budget")
            p,q,r=[points[i] for i in tri]
            n=cross(tuple(q[i]-p[i] for i in range(3)),tuple(r[i]-p[i] for i in range(3)))
            length=sqrt(sum(v*v for v in n))
            if length<1e-12:continue
            sign=1 if n[2]>=0 else -1
            encoded=bytes(max(0,min(255,round((sign*v/length+1)*127.5))) for v in n)+b"\xff"
            uv=[mesh.uv[i] for i in tri];colors=[mesh.colors[i] for i in tri] if mesh.colors else [(1.,)*4]*3
            for y in range(y0,y1):
                for x in range(x0,x1):
                    px,py=x+.5,y+.5
                    u=((b[1]-d[1])*(px-d[0])+(d[0]-b[0])*(py-d[1]))/den
                    v=((d[1]-a[1])*(px-d[0])+(a[0]-d[0])*(py-d[1]))/den
                    w=1-u-v
                    if min(u,v,w)<-1e-8:continue
                    i=y*size+x;z=u*a[2]+v*b[2]+w*d[2]
                    if z<=depth[i]:continue
                    tu,tv=(sum(weight*p[j] for weight,p in zip((u,v,w),uv)) for j in range(2))
                    tx=floor(tu*tw)%tw;ty=floor((1-tv)*th)%th
                    rgba=tex[(ty*tw+tx)*4:(ty*tw+tx+1)*4]
                    tinted=tuple(max(0,min(255,round(rgba[j]*sum(weight*p[j] for weight,p in zip((u,v,w),colors))))) for j in range(4))
                    if cutout and tinted[3]<=getattr(mesh,"lod_alpha_threshold",128):continue
                    depth[i]=z;pixels[i*4:i*4+4]=bytes((*tinted[:3],255));normals[i*4:i*4+4]=encoded
    if not any(pixels[3::4]):raise ValueError("Empty foliage bake")
    return bytes(pixels),bytes(normals),{"span":span,"mid":mid,"width":span,"height":span,"bottom":bottom,"top":top,"source_hashes":hashes,"coverage":sum(v>0 for v in pixels[3::4])/(size*size)}

def atlas_billboard(groups,assets,views=2,size=128):
    if views not in (1,2,4):raise ValueError("Invalid view count")
    mesh=Mesh();diffuse=[];normal=[];hashes={}
    for i in range(views):
        angle=pi*i/views;rgba,n,info=bake(groups,assets,size,angle);key=str(i)
        diffuse.append(Tile(key,size,size,rgba));normal.append(Tile(key,size,size,n));hashes.update(info["source_hashes"])
        w=info["span"]/2;z=info["mid"]
        def point(x,h):return (cos(angle)*x,sin(angle)*x,h)
        mesh.add([point(-w,z-w),point(w,z-w),point(w,z+w),point(-w,z+w)],[(0,0),(1,0),(1,1),(0,1)],[(0,1,2),(0,2,3)],key)
    side=1
    while side<ceil(sqrt(views))*(size+8):side*=2
    color,layout=pack(diffuse,side,side,4);norm,other=pack(normal,side,side,4)
    if layout!=other:raise ValueError("Foliage atlas mismatch")
    for i in range(views):
        for j in range(i*4,i*4+4):
            u,v=mesh.uv[j];u,v=remap_uv(u,1-v,layout[str(i)]);mesh.uv[j]=(u,1-v)
    mesh.faces=[(f,"foliage") for f,_ in mesh.faces]
    n=len(mesh.vertices);mesh.vertices.extend(mesh.vertices[:]);mesh.uv.extend(mesh.uv[:])
    mesh.faces.extend(((c+n,b+n,a+n),m) for (a,b,c),m in mesh.faces[:])
    validate_mesh(mesh)
    return mesh,color,norm,side,layout,hashes

def source_groups(raw,profile):
    if profile=="oblivion":
        from .oblivion_lod_nif import read_static_groups
        from .oblivion_lod_nif import DEFAULT_MATERIAL
        groups=read_static_groups(raw)
        if any(material!=DEFAULT_MATERIAL for _,_,_,material in groups):raise ValueError("Nondefault legacy material needs explicit bake")
        return [(m,d,d[:-4]+"_n.dds",cut) for m,d,cut,_ in groups]
    if profile in ("new-vegas","fallout3"):
        from .fnv_lod_nif import read_static_groups
        return read_static_groups(raw,include_cutout=True)
    from .modern_lod_codec import read_static_groups
    return read_static_groups(raw,profile)
