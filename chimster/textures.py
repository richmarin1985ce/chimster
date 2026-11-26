"""Original deterministic texture generators. Data maps are linear, not sRGB.
Normal/specular generation uses authored height/mask inputs, not material inference."""
from pathlib import Path
import math,struct
from .atlas import write_png
from .lod_assets import dds_rgba,write_dds

FACES=("+X","-X","+Y","-Y","+Z","-Z")

def shape(w,h,raw,channels):
    if not isinstance(w,int) or not isinstance(h,int) or not 1<=w<=4096 or not 1<=h<=4096 or len(raw)!=w*h*channels:raise ValueError("invalid image dimensions")

def normal_map(w,h,height,strength=4.0,convention="directx",wrap=False,alpha=None):
    """Central differences on normalized grayscale height; image rows increase downward.
    DirectX Y is in increasing-V direction, OpenGL flips the green channel."""
    shape(w,h,height,1)
    if not math.isfinite(strength) or not 0<=strength<=256 or convention not in {"directx","opengl"}:raise ValueError("invalid normal settings")
    if alpha is not None:shape(w,h,alpha,1)
    def sample(x,y):
        if wrap:x%=w;y%=h
        else:x=max(0,min(w-1,x));y=max(0,min(h-1,y))
        return height[y*w+x]/255
    out=bytearray(w*h*4)
    for y in range(h):
        for x in range(w):
            dx=(sample(x+1,y)-sample(x-1,y))*strength*.5
            dy=(sample(x,y+1)-sample(x,y-1))*strength*.5
            nx,ny,nz=-dx,-dy if convention=="directx" else dy,1
            length=math.sqrt(nx*nx+ny*ny+1)
            i=y*w+x
            out[i*4:i*4+4]=bytes([round(127.5*(v/length+1)) for v in (nx,ny,nz)]+[alpha[i] if alpha is not None else 255])
    return bytes(out)

def specular_map(w,h,mask,low=.04,high=.5,gamma=1.0,invert=False):
    """Remap an explicit linear scalar mask to achromatic reflectivity.
    This is an artistic control, not a measured PBR reflectance estimate."""
    shape(w,h,mask,1)
    if not all(math.isfinite(x) for x in (low,high,gamma)) or not 0<=low<=high<=1 or not .01<=gamma<=10:raise ValueError("invalid specular settings")
    out=bytearray(w*h*4)
    for i,m in enumerate(mask):
        t=m/255
        if invert:t=1-t
        v=round(255*(low+(high-low)*t**gamma))
        out[4*i:4*i+4]=bytes((v,v,v,255))
    return bytes(out)

def direction(face,u,v):
    """DirectX cube orientation: u right, v down; longitude zero is +Z."""
    dirs={"+X":(1,-v,-u),"-X":(-1,-v,u),"+Y":(u,1,v),"-Y":(u,-1,-v),"+Z":(u,-v,1),"-Z":(-u,-v,-1)}
    x,y,z=dirs[face];n=math.sqrt(x*x+y*y+z*z)
    return x/n,y/n,z/n

def cube_from_panorama(w,h,rgba,size=128):
    shape(w,h,rgba,4)
    if w!=2*h or not isinstance(size,int) or not 1<=size<=1024:raise ValueError("expected 2:1 equirectangular panorama and face size 1..1024")
    def sample(x,y):
        ix=math.floor(x);iy=math.floor(y);fx=x-ix;fy=y-iy
        def at(a,b,c):return rgba[4*(max(0,min(h-1,b))*w+a%w)+c]
        return bytes(round((1-fy)*((1-fx)*at(ix,iy,c)+fx*at(ix+1,iy,c))+fy*((1-fx)*at(ix,iy+1,c)+fx*at(ix+1,iy+1,c))) for c in range(4))
    result={}
    for face in FACES:
        out=bytearray(size*size*4)
        for y in range(size):
            for x in range(size):
                dx,dy,dz=direction(face,2*(x+.5)/size-1,2*(y+.5)/size-1)
                lon=math.atan2(dx,dz);lat=math.asin(max(-1,min(1,dy)))
                px=(lon/(2*math.pi)+.5)*w-.5
                py=(.5-lat/math.pi)*h-.5
                i=4*(y*size+x);out[i:i+4]=sample(px,py)
        result[face]=bytes(out)
    return result

def cube_dds(size,faces):
    if set(faces)!=set(FACES):raise ValueError("all six faces required")
    first=dds_rgba(size,size,faces[FACES[0]])
    header=bytearray(first[:128])
    # DDSCAPS_TEXTURE | DDSCAPS_COMPLEX; DDSCAPS2_CUBEMAP | all six face bits.
    struct.pack_into("<II",header,108,0x1008,0xfe00)
    return bytes(header)+b"".join(dds_rgba(size,size,faces[f])[128:] for f in FACES)

def mip_chain(w,h,raw,normal=False):
    """Linear scalar/color box mips; normal vectors are renormalized.
    No alpha-test coverage adjustment, gamma conversion or cubemap filtering."""
    shape(w,h,raw,4)
    levels=[(w,h,raw)]
    while w>1 or h>1:
        nw,nh=max(1,w//2),max(1,h//2);out=bytearray(nw*nh*4)
        for y in range(nh):
            for x in range(nw):
                # Include every source texel, even when dimensions are odd.
                points=[4*(j*w+i) for j in range(y*h//nh,(y+1)*h//nh) for i in range(x*w//nw,(x+1)*w//nw)]
                values=[sum(raw[p+c] for p in points)/len(points) for c in range(4)]
                if normal:
                    v=[a/127.5-1 for a in values[:3]];length=math.sqrt(sum(a*a for a in v))
                    values[:3]=[127.5*(a/length+1) for a in v] if length>1e-6 else [128,128,255]
                i=4*(y*nw+x);out[i:i+4]=bytes(max(0,min(255,round(a))) for a in values)
        w,h,raw=nw,nh,bytes(out);levels.append((w,h,raw))
    return levels

def mip_dds(w,h,raw,normal=False):
    levels=mip_chain(w,h,raw,normal)
    header=bytearray(dds_rgba(w,h,raw)[:128])
    if len(levels)>1:
        struct.pack_into("<I",header,8,0x2100f)
        struct.pack_into("<I",header,28,len(levels))
        struct.pack_into("<I",header,108,0x401008)
    return bytes(header)+b"".join(dds_rgba(a,b,p)[128:] for a,b,p in levels)

def load_pixels(path,mode):
    from PIL import Image
    with Image.open(path) as im:
        w,h=im.size
        if not 1<=w<=4096 or not 1<=h<=4096:raise ValueError("image too large")
        return w,h,im.convert(mode).tobytes()

def build_material(height_path,mask_path,output,strength=4.0,convention="directx",wrap=False,pack_alpha=False,low=.04,high=.5):
    w,h,height=load_pixels(height_path,"L");mw,mh,mask=load_pixels(mask_path,"L")
    if (w,h)!=(mw,mh):raise ValueError("height and specular mask sizes differ")
    spec=specular_map(w,h,mask,low,high)
    normal=normal_map(w,h,height,strength,convention,wrap,spec[::4] if pack_alpha else None)
    p=Path(output);p.mkdir(parents=True,exist_ok=False)
    for name,raw in [("material_n",normal),("material_s",spec)]:
        write_png(p/(name+".png"),w,h,raw)
        with (p/(name+".dds")).open("xb") as f:f.write(mip_dds(w,h,raw,normal=name.endswith("_n")))
    return {"output":str(p),"dimensions":[w,h],"normal_convention":convention,"specular_in_normal_alpha":pack_alpha,"warning":"Uncompressed DDS with mipmaps; select target-specific material flags and texture packing before use."}

def build_cube(source,output,size=128):
    w,h,raw=load_pixels(source,"RGBA");faces=cube_from_panorama(w,h,raw,size)
    data=cube_dds(size,faces);p=Path(output);p.mkdir(parents=True,exist_ok=False)
    for name,rgba in faces.items():write_png(p/(name.replace("+","pos").replace("-","neg")+".png"),size,size,rgba)
    with (p/"environment.dds").open("xb") as f:f.write(data)
    return {"output":str(p),"face_size":size,"faces":list(FACES),"warning":"LDR bilinear panorama sampling; no HDR, prefiltered reflections, compression or mipmaps."}
