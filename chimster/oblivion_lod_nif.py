"""Original Oblivion 20.0.0.5 stream-11 textured static mesh candidate writer.

The old format has inline strings and no block-size table. This intentionally
supports a narrow, deterministic layout; independent game validation is pending.
"""
from .fnv_lod_nif import pack,string,geometry,Reader,decode_geometry
from math import isfinite

MAGIC=b"Gamebryo File Format, Version 20.0.0.5\n"
def net(name=""):return string(name)+pack("Ii",0,-1)
def av(name,props=()):
    return net(name)+pack("H13fI",14,0,0,0,1,0,0,0,1,0,0,0,1,1,len(props))+b"".join(pack("i",i) for i in props)+pack("i",-1)
def texture(path):
    path=path.replace("\\","/")
    if not path.isascii() or not path.lower().startswith("textures/") or not path.lower().endswith(".dds") or any(p in ("",".","..") or ":" in p or "\0" in p for p in path.split("/")):raise ValueError("Unsafe TES4 texture")
    return path.replace("/","\\")

DEFAULT_MATERIAL=(1.,1.,1.,1.,1.,1.,0.,0.,0.,0.,0.,0.,10.,1.)
def encode_groups(groups):
    if not 1<=len(groups)<=128:raise ValueError("Legacy material group limit")
    blocks=[None];children=[]
    for mesh,diffuse,cutout,material in groups:
        if len(material)!=14 or not all(isfinite(v) for v in material) or material[-1]!=1:raise ValueError("Unsupported material")
        data,_,_=geometry(mesh)
        path=texture(diffuse);i=len(blocks);children.append(i)
        props=(i+2,i+3,i+5) if cutout else (i+2,i+3)
        shape=av("LOD geometry "+str(len(children)),props)+pack("iiB",i+1,-1,0)
        texturing=net()+pack("IIBiIIIB",2,6,1,i+4,3,2,0,0)+bytes(5)+pack("I",0)
        source=net()+pack("B",1)+string(path)+pack("iIIIBB",-1,6,1,3,1,1)
        blocks.extend([("NiTriShape",shape),("NiTriShapeData",data),("NiMaterialProperty",net()+pack("14f",*material)),("NiTexturingProperty",texturing),("NiSourceTexture",source)])
        if cutout:blocks.append(("NiAlphaProperty",net()+pack("HB",0x1200,128)))
    blocks[0]=("NiNode",av("Chimster LOD")+pack("I",len(children))+b"".join(pack("i",i) for i in children)+pack("I",0))
    types=list(dict.fromkeys(t for t,b in blocks))
    header=MAGIC+pack("IBIII",0x14000005,1,11,len(blocks),11)+b"\x09Chimster\0\x01\0\x01\0"
    header+=pack("H",len(types))+b"".join(string(t) for t in types)+b"".join(pack("H",types.index(t)) for t,b in blocks)+pack("I",0)
    return header+b"".join(b for t,b in blocks)+pack("Ii",1,0)

def encode(mesh,diffuse,cutout=False):
    return encode_groups([(mesh,diffuse,cutout,DEFAULT_MATERIAL)])

def inspect(raw):
    groups,types=read_static_groups(raw,with_types=True)
    return {"triangles":sum(len(m.faces) for m,*_ in groups),"vertices":sum(len(m.vertices) for m,*_ in groups),
            "diffuse":groups[0][1] if len(groups)==1 else None,"cutout":any(c for _,_,c,_ in groups),
            "material_groups":len(groups),"colored_vertices":sum(len(getattr(m,"colors",[])) for m,*_ in groups),
            "block_types":types,"runtime_verified":False}

def read_static_groups(raw,with_types=False):
    """Read a bounded subset of actual TES4 static NIFs, including strip geometry.
    Unrecognized blocks cannot be skipped safely in this unsized legacy stream.
    """
    from .flora import Mesh
    from .lod import validate_mesh
    if len(raw)>64*1024*1024:raise ValueError("TES4 source size limit")
    r=Reader(raw)
    if r.take(len(MAGIC))!=MAGIC:raise ValueError("Not Oblivion NIF")
    version,endian,user,count,stream=r.get("IBIII")
    if (version,endian,stream)!=(0x14000005,1,11) or user not in (10,11) or not 1<=count<=2048:raise ValueError("Unsupported TES4 stream")
    for _ in range(3):r.take(r.get("B")[0])
    n,=r.get("H")
    if not 1<=n<=256:raise ValueError("Block type limit")
    types=[r.string().decode("ascii") for _ in range(n)]
    ids=[r.get("H")[0] for _ in range(count)]
    if any(i>=n for i in ids) or r.get("I")[0]!=0:raise ValueError("Unsupported block mapping")
    blocks=[]
    def obj():
        r.string();n,=r.get("I")
        if n>64:raise ValueError("Extra data limit")
        extra=[r.get("i")[0] for _ in range(n)]
        if r.get("i")[0]!=-1:raise ValueError("Animated source")
        return extra
    def avobj():
        extra=obj();flags,*t=r.get("H13f")
        if flags&1:raise ValueError("Hidden source node")
        if not all(isfinite(v) for v in t) or not 0<t[12]<=100:raise ValueError("Invalid transform")
        rot=t[3:12]
        if any(abs(sum(rot[i*3+k]*rot[j*3+k] for k in range(3))-(1 if i==j else 0))>1e-3 for i in range(3) for j in range(3)):raise ValueError("Nonorthogonal transform")
        det=rot[0]*(rot[4]*rot[8]-rot[5]*rot[7])-rot[1]*(rot[3]*rot[8]-rot[5]*rot[6])+rot[2]*(rot[3]*rot[7]-rot[4]*rot[6])
        if abs(det-1)>1e-3:raise ValueError("Mirrored transform")
        n,=r.get("I")
        if n>32:raise ValueError("Property limit")
        props=[r.get("i")[0] for _ in range(n)]
        if r.get("i")[0]!=-1:raise ValueError("Collision blocks not yet supported in legacy reader")
        return t,props,extra
    def geom(kind):
        _,n,_,_,has=r.get("iHBBB")
        if not n or not has:raise ValueError("Missing vertices")
        mesh=Mesh();mesh.vertices=[r.get("3f") for _ in range(n)]
        flags,has=r.get("HB")
        if flags&~0x1001 or not flags&1:raise ValueError("Unsupported UV layout")
        if has:r.take(n*12*(3 if flags&0x1000 else 1))
        r.take(16)
        mesh.colors=[]
        if r.get("B")[0]:
            mesh.colors=[r.get("4f") for _ in range(n)]
            if any(not all(isfinite(v) and 0<=v<=1 for v in rgba) for rgba in mesh.colors):raise ValueError("Invalid vertex colors")
        mesh.uv=[(u,1-v) for u,v in (r.get("2f") for _ in range(n))]
        _,additional,t=r.get("HiH")
        if additional!=-1 or not t:raise ValueError("Unsupported geometry extras")
        if kind=="NiTriShapeData":
            points,has=r.get("IB")
            if not has or points!=t*3:raise ValueError("Invalid triangle header")
            mesh.faces=[(r.get("3H"),"lod") for _ in range(t)]
            matches,=r.get("H")
            if matches>n:raise ValueError("Normal group limit")
            for _ in range(matches):
                k,=r.get("H")
                if k>n:raise ValueError("Normal group size")
                r.take(k*2)
        else:
            k,=r.get("H")
            if not 1<=k<=t:raise ValueError("Strip count")
            lengths=[r.get("H")[0] for _ in range(k)]
            if sum(lengths)>3*t+2*k or not r.get("B")[0]:raise ValueError("Invalid strip points")
            for length in lengths:
                strip=[r.get("H")[0] for _ in range(length)]
                for i in range(length-2):
                    a,b,c=strip[i:i+3]
                    if len({a,b,c})==3:mesh.faces.append(((b,a,c) if i%2 else (a,b,c),"lod"))
            if len(mesh.faces)>t:raise ValueError("Strip triangle count mismatch")
        validate_mesh(mesh);return mesh
    for index in ids:
        kind=types[index]
        if kind in ("NiNode","BSFadeNode"):
            t,props,extra=avobj();n,=r.get("I")
            if props or n>1024:raise ValueError("Unsupported node properties")
            value=(t,[r.get("i")[0] for _ in range(n)],extra)
            if r.get("I")[0]!=0:raise ValueError("Node effects unsupported")
        elif kind in ("NiTriShape","NiTriStrips"):
            t,props,extra=avobj();data,skin,shader=r.get("iiB")
            if skin!=-1 or shader:raise ValueError("Skinned or custom shader source")
            value=(t,props,extra,data)
        elif kind in ("NiTriShapeData","NiTriStripsData"):value=geom(kind)
        elif kind=="NiMaterialProperty":
            if obj():raise ValueError("Material extras")
            value=r.get("14f")
            if not all(isfinite(v) for v in value) or value[-1]!=1:raise ValueError("Unsupported translucent material")
        elif kind=="NiTexturingProperty":
            if obj():raise ValueError("Texture property extras")
            apply,n=r.get("II")
            if apply not in (0,2) or not 5<=n<=10:raise ValueError("Unsupported texture slots")
            value=None
            for i in range(n):
                if r.get("B")[0]:
                    if i!=0:raise ValueError("Additional texture layers")
                    source,clamp,filter_mode,uv,trans=r.get("iIIIB")
                    if clamp not in (0,3) or uv or trans:raise ValueError("Texture coordinate transform")
                    value=source
            if r.get("I")[0]!=0 or value is None:raise ValueError("Unsupported texture shader slots")
        elif kind=="NiSourceTexture":
            if obj() or r.get("B")[0]!=1:raise ValueError("Embedded texture unsupported")
            value=r.string().decode("ascii").replace("\\","/")
            if r.get("i")[0]!=-1:raise ValueError("Embedded pixel data")
            r.take(14)
            texture(value)
        elif kind=="NiAlphaProperty":
            if obj():raise ValueError("Alpha extras")
            flags,threshold=r.get("HB")
            if flags&1 or flags&0x1e00!=0x1200 or threshold!=128:raise ValueError("Unsupported alpha mode")
            value=True
        elif kind=="NiStringExtraData":
            r.string();r.string();value=None
        elif kind in ("NiIntegerExtraData","BSXFlags"):
            r.string();r.get("I");value=None
        else:raise ValueError("Unsupported unsized TES4 block "+kind)
        blocks.append((kind,value))
    roots,=r.get("I")
    if not 1<=roots<=32:raise ValueError("Invalid root count")
    root_ids=[r.get("i")[0] for _ in range(roots)]
    if r.i!=len(raw):raise ValueError("Trailing source bytes")
    def ref(i,kinds):
        if not 0<=i<len(blocks) or blocks[i][0] not in kinds:raise ValueError("Invalid block reference")
        return blocks[i][1]
    groups={};seen=set()
    def visit(i,chain=()):
        if i in seen or len(chain)>32 or not 0<=i<len(blocks):raise ValueError("Invalid source graph")
        seen.add(i);kind,value=blocks[i]
        if kind in ("NiNode","BSFadeNode"):
            t,children,extra=value
            for child in children:visit(child,(t,)+chain)
            return
        if kind not in ("NiTriShape","NiTriStrips"):raise ValueError("Unsupported render node")
        t,props,extra,data=value;chain=(t,)+chain
        paths=[];cut=False;material=DEFAULT_MATERIAL;material_seen=False
        for p in props:
            if not 0<=p<len(blocks):raise ValueError("Invalid property")
            k,v=blocks[p]
            if k=="NiTexturingProperty":paths.append(ref(v,{"NiSourceTexture"}))
            elif k=="NiAlphaProperty":cut=True
            elif k=="NiMaterialProperty":
                if material_seen:raise ValueError("Multiple material properties")
                material=v;material_seen=True
            else:raise ValueError("Unsupported property")
        if len(paths)!=1:raise ValueError("Exactly one diffuse texture required")
        mesh=ref(data,{"NiTriShapeData","NiTriStripsData"});target=groups.setdefault((paths[0],cut,material),Mesh());offset=len(target.vertices)
        if offset+len(mesh.vertices)>65535 or len(target.faces)+len(mesh.faces)>65535:raise ValueError("Legacy shape budget")
        for p in mesh.vertices:
            for t in chain:p=tuple(t[i]+t[12]*sum(t[3+i*3+j]*p[j] for j in range(3)) for i in range(3))
            target.vertices.append(p)
        colors=getattr(mesh,"colors",[]);old=getattr(target,"colors",[])
        if colors or old:target.colors=(old or [(1.,)*4]*offset)+(colors or [(1.,)*4]*len(mesh.vertices))
        target.uv.extend(mesh.uv);target.faces.extend((tuple(v+offset for v in f),"lod") for f,_ in mesh.faces)
    for root in root_ids:visit(root)
    if not groups:raise ValueError("No supported legacy geometry")
    result=[(mesh,*key) for key,mesh in sorted(groups.items())]
    for mesh,*_ in result:validate_mesh(mesh)
    return (result,[kind for kind,_ in blocks]) if with_types else result

def read_static(raw):
    groups=read_static_groups(raw)
    if len(groups)!=1:raise ValueError("Multiple material groups; use grouped reader")
    mesh,path,cutout,_=groups[0]
    return mesh,path,cutout
