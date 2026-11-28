"""In-process Skyrim LE/SSE and Fallout 4 static LOD mesh candidates.
No external application or third-party runtime. Format-specific stream layouts
are deliberately separate from the classic stream-34 reader.
"""
from math import sqrt,isfinite
from .fnv_lod_nif import MAGIC,pack,string,net,geometry,Reader
from .flora import Mesh
from .lod import validate_mesh

STREAMS={"skyrim":83,"skyrim-se":100,"fallout4":130}

def av(name):
    return net(name)+pack("I13fi",14,0,0,0,1,0,0,0,1,0,0,0,1,1,-1)

def texture_path(path):
    path=path.replace("\\","/")
    if not path.isascii() or not path.lower().startswith("textures/") or not path.lower().endswith(".dds") or any(p in ("",".","..") or ":" in p or "\0" in p for p in path.split("/")):
        raise ValueError("Unsafe DDS path")
    return path.replace("/","\\")

def header(blocks,names,stream):
    types=list(dict.fromkeys(t for t,b in blocks))
    raw=MAGIC+pack("IBIII",0x14020007,1,12,len(blocks),stream)+b"\x09Chimster\0\x01\0\x01\0"
    if stream>=103:raw+=b"\x01\0"
    raw+=pack("H",len(types))+b"".join(string(t) for t in types)
    raw+=b"".join(pack("H",types.index(t)) for t,b in blocks)
    raw+=b"".join(pack("I",len(b)) for t,b in blocks)
    raw+=pack("II",len(names),max(map(len,names)))+b"".join(string(s) for s in names)+pack("I",0)
    return raw+b"".join(b for t,b in blocks)+pack("Ii",1,0)

def shader(tex,stream,kind,cutout):
    typ=9 if kind=="terrain" else 13 if kind=="object" else 0
    f1=0x80000100|(0x4000 if kind=="terrain" else 0)
    f2=1|({"terrain":2,"object":4,"companion":0}[kind])|(16 if cutout else 0)
    raw=pack("I",typ)+net()+pack("II4fi4f",f1,f2,0,0,1,1,tex,0,0,0,1)
    if stream==130:raw+=pack("i",-1)
    raw+=pack("I3f4f",3,1,0,1 if stream==130 else 16,1,1,1,0)
    if stream==130:
        # Subsurface, rim, backlight, grayscale, Fresnel, six wetness parameters.
        raw+=pack("11f",0,3.402823466e38,0,1,5,*([-1]*6))
    else:raw+=pack("2f",.3,2)
    return raw

def packed_geometry(mesh,raw,center,stream,shader_id,alpha_id,name):
    # The classic geometry builder supplies validated normals and tangent frames.
    r=Reader(raw);_,n,_,_,has=r.get("iHBBB")
    if not has:raise ValueError("Missing vertices")
    vs=[r.get("3f") for _ in range(n)]
    flags,has=r.get("HB")
    if flags!=0x1001 or not has:raise ValueError("Missing tangent space")
    ns=[r.get("3f") for _ in range(n)]
    ts=[r.get("3f") for _ in range(n)]
    bs=[r.get("3f") for _ in range(n)]
    sphere=r.get("4f")
    if r.get("B")[0]:raise ValueError("Unexpected vertex colors")
    uv=[r.get("2f") for _ in range(n)]
    _,_,t,points,has=r.get("HiHIB")
    if not has or points!=t*3:raise ValueError("Invalid triangles")
    triangles=r.take(t*6)
    def byte(v):return max(0,min(255,round((v+1)*127.5)))
    # 28-byte vertex: full XYZ + bitangent X, half UV, two packed vectors.
    desc=7|(4<<8)|(5<<16)|(6<<20)|((0x41b if stream==130 else 0x1b)<<44)
    data=b"".join(pack("4f2e8B",*v,b[0],*u,*map(byte,nn),byte(b[1]),*map(byte,tt),byte(b[2])) for v,b,u,nn,tt in zip(vs,bs,uv,ns,ts))
    return av(name)+pack("4fiiiQ",*sphere,-1,shader_id,alpha_id,desc)+pack("IH" if stream==130 else "HH",t,n)+pack("I",len(data)+len(triangles))+data+triangles+(pack("I",0) if stream==100 else b"")

def encode_groups(groups,profile,kind="terrain"):
    if profile not in STREAMS or kind not in ("terrain","object","companion") or not 1<=len(groups)<=128:raise ValueError("Unsupported modern LOD layout")
    stream=STREAMS[profile];blocks=[None];names=[b"Chimster LOD"];children=[];bounds=[]
    for group in groups:
        mesh,diffuse,normal=group[:3];cutout=group[3] if len(group)==4 else False
        if type(cutout)!=bool:raise ValueError("Invalid cutout mode")
        d,n=texture_path(diffuse),texture_path(normal)
        data,center,extent=geometry(mesh)
        bounds.extend(tuple(center[i]+sign*extent[i] for i in range(3)) for sign in (-1,1))
        i=len(blocks);children.append(i);names.append(("LOD "+str(len(children))).encode())
        sid=i+2 if stream==83 else i+1;tid=sid+1;aid=tid+1 if cutout else -1
        if stream==83:
            # Stream 83 NiGeometryData inserts a material CRC before Has Normals.
            pos=9+len(mesh.vertices)*12+2
            geom=data[:pos]+pack("I",0)+data[pos:]
            shape=av(len(names)-1)+pack("iiIiBii",i+1,-1,0,-1,0,sid,aid)
            blocks.extend([("NiTriShape",shape),("NiTriShapeData",geom)])
        else:
            shape=packed_geometry(mesh,data,center,stream,sid,aid,len(names)-1)
            blocks.append(("BSTriShape",shape))
        blocks.extend([("BSLightingShaderProperty",shader(tid,stream,kind,cutout)),
                       ("BSShaderTextureSet",pack("I",9)+b"".join(string(p) for p in (d,n,"","","","","","","")))])
        if cutout:blocks.append(("NiAlphaProperty",net()+pack("HB",0x1200,128)))
    lo=tuple(min(p[i] for p in bounds) for i in range(3));hi=tuple(max(p[i] for p in bounds) for i in range(3))
    center=tuple((a+b)/2 for a,b in zip(lo,hi));extent=tuple((b-a)/2 for a,b in zip(lo,hi))
    i=len(blocks)
    blocks[0]=("BSMultiBoundNode",av(0)+pack("I",len(children))+b"".join(pack("i",c) for c in children)+(pack("I",0) if stream<130 else b"")+pack("iI",i,0))
    blocks.extend([("BSMultiBound",pack("i",i+1)),("BSMultiBoundAABB",pack("6f",*center,*extent))])
    return header(blocks,names,stream)

def inspect(raw,profile):
    """Bounded structural audit of own candidate stream, not game verification."""
    stream=STREAMS[profile];r=Reader(raw)
    if r.take(len(MAGIC))!=MAGIC or r.get("IBIII")[:3]!=(0x14020007,1,12):raise ValueError("Invalid header")
    r.i=len(MAGIC);_,_,_,count,actual=r.get("IBIII")
    if actual!=stream or not 1<=count<=1024:raise ValueError("Unexpected stream")
    for _ in range(4 if stream>=103 else 3):r.take(r.get("B")[0])
    k,=r.get("H")
    if not 1<=k<=256:raise ValueError("Block type limit")
    types=[r.string().decode("ascii") for _ in range(k)]
    ids=[r.get("H")[0] for _ in range(count)]
    if any(i>=k for i in ids):raise ValueError("Invalid block ID")
    sizes=[r.get("I")[0] for _ in ids];n,maxlen=r.get("II")
    if n>1024 or maxlen>65536:raise ValueError("String budget")
    for _ in range(n):r.string()
    if r.get("I")[0]!=0:raise ValueError("Unsupported groups")
    blocks=[(types[i],r.take(s)) for i,s in zip(ids,sizes)]
    if r.get("Ii")!=(1,0) or r.i!=len(raw):raise ValueError("Invalid footer")
    triangles=vertices=0
    for typ,data in blocks:
        if typ=="NiTriShapeData":
            from .fnv_lod_nif import decode_geometry
            q=Reader(data);_,n,_,_,_=q.get("iHBBB");pos=9+n*12+2
            m=decode_geometry(data[:pos]+data[pos+4:]);triangles+=len(m.faces);vertices+=len(m.vertices)
        elif typ=="BSTriShape":
            q=Reader(data);q.take(72);q.take(16+12)
            desc,=q.get("Q");t,n=q.get("IH" if stream==130 else "HH");size,=q.get("I")
            if (desc&15)!=7 or size!=n*28+t*6 or not n or not t:raise ValueError("Invalid packed geometry")
            q.take(n*28)
            for _ in range(t):
                if any(i>=n for i in q.get("3H")):raise ValueError("Invalid packed triangle")
            if stream==100 and q.get("I")[0]!=0:raise ValueError("Unexpected particle data")
            if q.i!=len(data):raise ValueError("Unexpected shape tail")
            triangles+=t;vertices+=n
    if not triangles:raise ValueError("Missing geometry")
    return {"stream":stream,"triangles":triangles,"vertices":vertices,"block_types":[t for t,_ in blocks],"runtime_verified":False}


def export_tile(profile,kind,world,level,x,y,mesh,diffuse,normal,output,cutout=False):
    """Export a single author-supplied tile in the native candidate naming scheme."""
    import re
    from pathlib import Path
    from hashlib import sha256
    if kind not in ("terrain","object") or not re.fullmatch(r"[A-Za-z0-9_ -]{1,128}",world):
        raise ValueError("Invalid world or tile kind")
    if level not in (4,8,16,32) or any(type(v)!=int or not -32768<=v<=32767 for v in (x,y)):
        raise ValueError("Invalid tile coordinates")
    if kind=="terrain" and cutout:raise ValueError("Terrain does not support cutout")
    raw=encode_groups([(mesh,diffuse,normal,cutout)],profile,kind)
    report=inspect(raw,profile)
    if report["triangles"]!=len(mesh.faces):raise ValueError("Geometry roundtrip mismatch")
    root=Path(output).resolve()
    root.mkdir(parents=True,exist_ok=True)
    base=root/"meshes"/"terrain"/world
    if kind=="object":base=base/"objects"
    dest=base/(f"{world}.{level}.{x}.{y}."+("btr" if kind=="terrain" else "bto"))
    if not dest.resolve().is_relative_to(root):raise ValueError("Output escapes root")
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open("xb") as f:f.write(raw)
    return {**report,"path":str(dest),"sha256":sha256(raw).hexdigest(),"external_tools":False,
            "scope":"Author-supplied tile mesh in local game units, material and runtime layout require validation"}
