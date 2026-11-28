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

def default_tail(stream):
    raw=pack("4f",0,0,0,1)
    if stream==130:raw+=pack("i",-1)
    raw+=pack("I3f4f",3,1,0,1 if stream==130 else 16,1,1,1,0)
    if stream==130:raw+=pack("11f",0,3.402823466e38,0,1,5,*([-1]*6))
    else:raw+=pack("2f",.3,2)
    return raw

def validate_tail(tail,stream):
    r=Reader(tail)
    emission=r.get("4f")
    if stream==130 and r.get("i")[0]!=-1:raise ValueError("External root material unsupported")
    clamp,alpha,refract,gloss,*spec=r.get("I3f4f")
    if clamp!=3 or alpha!=1 or refract!=0:raise ValueError("Unsupported clamp, opacity or refraction")
    # Only exact known-length static shader tails can be preserved.
    values=list(emission)+[alpha,refract,gloss,*spec]
    if stream==130:
        subsurface,rim=r.get("2f");values.extend((subsurface,rim))
        if rim>=3.4028234e38:values.extend(r.get("f"))
        values.extend(r.get("8f"))
    else:values.extend(r.get("2f"))
    if r.i!=len(tail) or not all(isfinite(v) for v in values):raise ValueError("Unsupported shader tail")
    return tail

def shader(tex,stream,kind,cutout,colored=False,metadata=()):
    typ=9 if kind=="terrain" else 13 if kind=="object" else 0
    f1=(0x80000000 if stream==130 else 0x80000100)|(0x4000 if kind=="terrain" else 0)
    f2=1|({"terrain":2,"object":4,"companion":0}[kind])|(16 if cutout else 0)|(32 if colored else 0)
    tail=default_tail(stream)
    if metadata:
        source_stream,source_f1,source_f2,tailhex,threshold=metadata
        if source_stream!=stream:raise ValueError("Shader metadata stream mismatch")
        tail=validate_tail(bytes.fromhex(tailhex),stream)
        # Preserve static appearance flags, not gameplay/dynamic animation flags.
        f1|=source_f1&(0x00400209 if stream==130 else 0x00400309)
        f2|=source_f2&0x10
    if stream==130 and cutout:f2|=1<<25
    return pack("I",typ)+net()+pack("II4fi",f1,f2,0,0,1,1,tex)+tail

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
    colors=[r.get("4f") for _ in range(n)] if r.get("B")[0] else []
    uv=[r.get("2f") for _ in range(n)]
    _,_,t,points,has=r.get("HiHIB")
    if not has or points!=t*3:raise ValueError("Invalid triangles")
    triangles=r.take(t*6)
    def byte(v):return max(0,min(255,round((v+1)*127.5)))
    # 28-byte vertex: full XYZ + bitangent X, half UV, two packed vectors.
    desc=(8 if colors else 7)|(4<<8)|(5<<16)|(6<<20)|((7<<24) if colors else 0)|(((0x41b if stream==130 else 0x1b)|(32 if colors else 0))<<44)
    data=b"".join(pack("4f2e8B",*v,b[0],*u,*map(byte,nn),byte(b[1]),*map(byte,tt),byte(b[2]))+(bytes(round(x*255) for x in colors[i]) if colors else b"") for i,(v,b,u,nn,tt) in enumerate(zip(vs,bs,uv,ns,ts)))
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
        blocks.extend([("BSLightingShaderProperty",shader(tid,stream,kind,cutout,bool(mesh.colors),getattr(mesh,"lod_shader",()))),
                       ("BSShaderTextureSet",pack("I",9)+b"".join(string(p) for p in (d,n,"","","","","","","")))])
        if cutout:
            threshold=getattr(mesh,"lod_alpha_threshold",128)
            if type(threshold)!=int or not 0<=threshold<=255:raise ValueError("Invalid alpha threshold")
            blocks.append(("NiAlphaProperty",net()+pack("HB",0x1200,threshold)))
    lo=tuple(min(p[i] for p in bounds) for i in range(3));hi=tuple(max(p[i] for p in bounds) for i in range(3))
    center=tuple((a+b)/2 for a,b in zip(lo,hi));extent=tuple((b-a)/2 for a,b in zip(lo,hi))
    i=len(blocks)
    blocks[0]=("BSMultiBoundNode",av(0)+pack("I",len(children))+b"".join(pack("i",c) for c in children)+(pack("I",0) if stream<130 else b"")+pack("iI",i,0))
    blocks.extend([("BSMultiBound",pack("i",i+1)),("BSMultiBoundAABB",pack("6f",*center,*extent))])
    return header(blocks,names,stream)

def read_blocks(raw,profile):
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
    return blocks

def inspect(raw,profile):
    stream=STREAMS[profile];blocks=read_blocks(raw,profile)
    triangles=vertices=0
    for typ,data in blocks:
        if typ=="NiTriShapeData":
            from .fnv_lod_nif import decode_geometry
            q=Reader(data);_,n,_,_,_=q.get("iHBBB");pos=9+n*12+2
            m=decode_geometry(data[:pos]+data[pos+4:]);triangles+=len(m.faces);vertices+=len(m.vertices)
        elif typ=="BSTriShape":
            q=Reader(data);q.take(72);q.take(16+12)
            desc,=q.get("Q");t,n=q.get("IH" if stream==130 else "HH");size,=q.get("I")
            stride=(desc&15)*4
            if size!=n*stride+t*6 or not n or not t:raise ValueError("Invalid packed geometry")
            read_packed_vertices(q,desc,n,stream,preserve_colors=True)
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


def read_packed_vertices(r,desc,count,stream,preserve_colors=False):
    """Read documented unskinned static vertex variants, rejecting lossy attributes."""
    flags=desc>>44
    if flags&~0x43b or flags&3!=3 or flags&16 and not flags&8:
        raise ValueError("Unsupported packed attributes")
    full=stream==100 or bool(flags&0x400)
    tangent=bool(flags&16);normal=bool(flags&8);color=bool(flags&32)
    stride=(desc&15)*4
    expected=(16 if full else 8)+4+4*normal+4*tangent+4*color
    if stride!=expected:raise ValueError("Packed vertex stride mismatch")
    uv_offset=(16 if full else 8)//4
    if (desc>>8)&15!=uv_offset:raise ValueError("UV offset mismatch")
    if normal and ((desc>>16)&15)!=uv_offset+1:raise ValueError("Normal offset mismatch")
    if tangent and ((desc>>20)&15)!=uv_offset+2:raise ValueError("Tangent offset mismatch")
    if color and ((desc>>24)&15)!=uv_offset+1+normal+tangent:raise ValueError("Color offset mismatch")
    mesh=Mesh()
    for _ in range(count):
        x,y,z,_=r.get("4f" if full else "4e")
        u,v=r.get("2e")
        if normal:r.take(4)
        if tangent:r.take(4)
        if color:
            rgba=r.take(4)
            if preserve_colors:mesh.colors.append(tuple(v/255 for v in rgba))
            elif rgba!=bytes([255])*4:raise ValueError("Nonwhite source vertex colors require color-preserving conversion")
        if not all(isfinite(a) for a in (x,y,z,u,v)):raise ValueError("Nonfinite packed vertex")
        mesh.vertices.append((x,y,z));mesh.uv.append((u,1-v))
    return mesh

def read_static_groups(raw,profile):
    """Read supported ordinary modern source geometry with explicit shader guards.
    No animation, skinning, external material files or complex shader conversion.
    """
    from .fnv_lod_nif import decode_geometry
    blocks=read_blocks(raw,profile);stream=STREAMS[profile]
    inert={"NiStringExtraData","NiIntegerExtraData","BSXFlags","BSBound","NiBinaryExtraData","BSBehaviorGraphExtraData"}
    def ref(i,kinds):
        if not 0<=i<len(blocks) or blocks[i][0] not in kinds:raise ValueError("Unexpected source block reference")
        return blocks[i][1]
    def av_read(data):
        r=Reader(data);_,count=r.get("iI")
        if count>64:raise ValueError("Extra data limit")
        for _ in range(count):ref(r.get("i")[0],inert)
        if r.get("i")[0]!=-1:raise ValueError("Animated source")
        flags,*t=r.get("I13f");collision,=r.get("i")
        if not all(isfinite(v) for v in t) or not 0<t[12]<=100:raise ValueError("Invalid source transform")
        if any(abs(sum(t[3+3*i+k]*t[3+3*j+k] for k in range(3))-(1 if i==j else 0))>1e-3 for i in range(3) for j in range(3)):raise ValueError("Invalid source rotation")
        if collision!=-1 and (not 0<=collision<len(blocks) or not blocks[collision][0].startswith("bhk")):raise ValueError("Unsupported collision")
        return r,t
    def material(sid,aid):
        r=Reader(ref(sid,{"BSLightingShaderProperty"}))
        typ,shader_name,extra,controller=r.get("IiIi")
        if typ not in (0,9,12,13,15) or extra or controller!=-1 or shader_name!=-1:raise ValueError("Unsupported named, animated or complex material")
        f1,f2,u,v,s,t,tid=r.get("II4fi")
        allowed1=0x82404309 if stream<130 else 0x80404309
        allowed2=0xa0008037 if stream<130 else 0x22008037
        if not all(isfinite(a) and abs(a)<=1024 for a in (u,v,s,t)) or not s or not t or f1&~allowed1 or f2&~allowed2:raise ValueError("Unsupported shader flags or UV transform")
        tail=validate_tail(r.take(len(r.raw)-r.i),stream)
        # No alpha blending, parallax, environment mapping or vertex-color loss.
        q=Reader(ref(tid,{"BSShaderTextureSet"}));n,=q.get("I")
        if not 2<=n<=10:raise ValueError("Texture set count")
        paths=[q.string().decode("ascii").replace("\\","/") for _ in range(n)]
        if not paths[0] or not paths[1] or any(paths[2:]) or q.i!=len(q.raw):raise ValueError("Unsupported additional texture layers")
        cut=aid!=-1;threshold=128
        if cut:
            a=Reader(ref(aid,{"NiAlphaProperty"}))
            _,extra,controller=a.get("iIi");flags,threshold=a.get("HB")
            if extra or controller!=-1 or flags&1 or flags&0x1e00!=0x1200 or a.i!=len(a.raw):raise ValueError("Unsupported alpha test")
        if stream==130 and f2&(1<<25) and not cut:raise ValueError("Alpha test flag without alpha property")
        appearance1=f1&0x00400309;appearance2=f2&0x10
        metadata=(stream,appearance1,appearance2,tail.hex(),threshold)
        return (paths[0],paths[1],cut),metadata,(u,v,s,t)
    seen=set();groups={}
    def visit(i,chain=()):
        if i in seen or len(chain)>32 or not 0<=i<len(blocks):raise ValueError("Invalid source graph")
        seen.add(i);kind,data=blocks[i];r,t=av_read(data);chain=(t,)+chain
        if kind in ("NiNode","BSFadeNode","BSMultiBoundNode"):
            count,=r.get("I")
            if count>1024:raise ValueError("Source child limit")
            for _ in range(count):visit(r.get("i")[0],chain)
            if stream<130 and r.get("I")[0]!=0:raise ValueError("Unsupported node effects")
            if kind=="BSMultiBoundNode":r.take(8)
            if r.i!=len(data):raise ValueError("Unsupported source node tail")
            return
        if kind=="NiTriShape" and stream==83:
            geom,skin,n,active,update,sid,aid=r.get("iiIiBii")
            if skin!=-1 or n:raise ValueError("Unsupported skin/material data")
            raw=ref(geom,{"NiTriShapeData"});q=Reader(raw);_,n,_,_,_=q.get("iHBBB");pos=9+n*12+2
            mesh=decode_geometry(raw[:pos]+raw[pos+4:])
        elif kind=="BSTriShape" and stream>=100:
            r.take(16);skin,sid,aid,desc=r.get("iiiQ")
            if skin!=-1:raise ValueError("Skinned source")
            t,n=r.get("IH" if stream==130 else "HH");size,=r.get("I")
            stride=(desc&15)*4
            if size!=n*stride+t*6 or not n or not t or t>65535:raise ValueError("Unsupported packed source geometry")
            mesh=read_packed_vertices(r,desc,n,stream,preserve_colors=True)
            mesh.faces=[(r.get("3H"),"lod") for _ in range(t)]
            if stream==100 and r.get("I")[0]!=0:raise ValueError("Particle data unsupported")
        else:raise ValueError("Unsupported source shape "+kind)
        if r.i!=len(data):raise ValueError("Unsupported source shape tail")
        key,metadata,uv_transform=material(sid,aid)
        target=groups.setdefault((*key,metadata),Mesh());offset=len(target.vertices)
        baseline=0 if stream==130 else 0x100
        canonical=(metadata[1]==baseline and metadata[2]==(16 if key[2] else 0) and metadata[3]==default_tail(stream).hex())
        target.lod_shader=() if canonical else metadata
        target.lod_alpha_threshold=metadata[-1]
        if offset+len(mesh.vertices)>100000 or len(target.faces)+len(mesh.faces)>100000:raise ValueError("Source geometry budget")
        validate_mesh(mesh)
        for p in mesh.vertices:
            for t in chain:p=tuple(t[i]+t[12]*sum(t[3+3*i+j]*p[j] for j in range(3)) for i in range(3))
            target.vertices.append(p)
        if mesh.colors or target.colors:
            if not target.colors:target.colors=[(1.,)*4]*offset
            target.colors.extend(mesh.colors or [(1.,)*4]*len(mesh.vertices))
        ou,ov,su,sv=uv_transform
        target.uv.extend((u*su+ou,1-((1-v)*sv+ov)) for u,v in mesh.uv);target.faces.extend((tuple(v+offset for v in f),"lod") for f,_ in mesh.faces)
    visit(0)
    if not groups:raise ValueError("No supported source geometry")
    for mesh in groups.values():validate_mesh(mesh)
    return [(m,*key[:3]) for key,m in sorted(groups.items())]
