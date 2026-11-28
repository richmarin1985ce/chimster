"""Original, dependency-free FO3/FNV 20.2.0.7 stream-34 static LOD NIF codec.

Narrow static geometry layout, documented NIF fields only. No external binaries.
Specialized Bethesda runtime LOD behavior is not yet independently verified.
"""
import struct
from math import sqrt,isfinite
from .flora import Mesh,cross
from .lod import validate_mesh

MAGIC=b"Gamebryo File Format, Version 20.2.0.7\n"
def pack(fmt,*v):return struct.pack("<"+fmt,*v)
def string(s):
    b=s.encode("ascii") if isinstance(s,str) else s
    return pack("I",len(b))+b
def net(name=-1):return pack("iIi",name,0,-1)
def av(name,props=()):
    return net(name)+pack("I13fI",0x8000e,0,0,0,1,0,0,0,1,0,0,0,1,1,len(props))+b"".join(pack("i",p) for p in props)+pack("i",-1)

def geometry(mesh):
    validate_mesh(mesh)
    n=len(mesh.vertices);t=len(mesh.faces)
    if not 0<n<=65535 or not 0<t<=65535:raise ValueError("NIF shape exceeds 16-bit limits")
    if any(len(face)!=3 for face,_ in mesh.faces):raise ValueError("Expected triangles")
    verts=mesh.vertices
    lo=tuple(min(v[i] for v in verts) for i in range(3));hi=tuple(max(v[i] for v in verts) for i in range(3))
    center=tuple((a+b)/2 for a,b in zip(lo,hi))
    radius=max(sqrt(sum((p[i]-center[i])**2 for i in range(3))) for p in verts)
    normals=[[0.,0.,0.] for _ in verts]
    for (a,b,c),_ in mesh.faces:
        normal=cross(tuple(verts[b][i]-verts[a][i] for i in range(3)),tuple(verts[c][i]-verts[a][i] for i in range(3)))
        for k in (a,b,c):
            for i in range(3):normals[k][i]+=normal[i]
    def unit(v):
        r=sqrt(sum(x*x for x in v));return tuple(x/r for x in v) if r else (0,0,1)
    body=pack("iHBBB",0,n,0,0,1)+b"".join(pack("3f",*v) for v in verts)
    body+=pack("HB",1,1)+b"".join(pack("3f",*unit(v)) for v in normals)
    body+=pack("4fB",*center,radius,0)+b"".join(pack("2f",u,1-v) for u,v in mesh.uv)
    body+=pack("HiHIB",0x4000,-1,t,t*3,1)+b"".join(pack("3H",*f) for f,_ in mesh.faces)+pack("H",0)
    return body,center,tuple((b-a)/2 for a,b in zip(lo,hi))

def encode(mesh,diffuse,normal,kind="terrain",segmented=False):
    if kind not in ("terrain","object","companion"):raise ValueError("Unknown LOD shader")
    for path in (diffuse,normal):
        if not path.isascii() or not path.lower().endswith(".dds") or not path.lower().startswith("textures/") or any(p in ("",".","..") or ":" in p for p in path.split("/")):raise ValueError("Unsafe DDS path")
    data,center,extent=geometry(mesh)
    names=[b"Chimster LOD",b"LOD Geometry"]
    root=av(0)+pack("IiI",1,1,0)+pack("i",5)
    shape=av(1,(3,))+pack("iiIiB",2,-1,0,-1,0)
    shape_type="NiTriShape"
    if segmented:
        shape_type="BSSegmentedTriShape"
        shape+=pack("I",1)+pack("BII",0,0,len(mesh.faces))
    flag={"terrain":2,"object":4,"companion":0}[kind]
    shader=net()+pack("HIIIfIififf",1,1,0x80000000,1|flag,1.,0,4,0.,0,4.,1.)
    textures=pack("I",6)+b"".join(string(p.replace("/","\\")) for p in (diffuse,normal,"","","",""))
    blocks=[("BSMultiBoundNode",root),(shape_type,shape),("NiTriShapeData",data),
            ("BSShaderPPLightingProperty",shader),("BSShaderTextureSet",textures),
            ("BSMultiBound",pack("i",6)),("BSMultiBoundAABB",pack("6f",*center,*extent))]
    types=list(dict.fromkeys(t for t,_ in blocks))
    header=MAGIC+pack("IBIII",0x14020007,1,11,len(blocks),34)+b"\x09Chimster\0\x01\0\x01\0"
    header+=pack("H",len(types))+b"".join(string(t) for t in types)
    header+=b"".join(pack("H",types.index(t)) for t,_ in blocks)+b"".join(pack("I",len(b)) for _,b in blocks)
    header+=pack("II",len(names),max(map(len,names)))+b"".join(string(s) for s in names)+pack("I",0)
    return header+b"".join(b for _,b in blocks)+pack("Ii",1,0)

class Reader:
    def __init__(self,raw):self.raw=raw;self.i=0
    def take(self,n):
        if n<0 or self.i+n>len(self.raw):raise ValueError("Truncated NIF")
        out=self.raw[self.i:self.i+n];self.i+=n;return out
    def get(self,fmt):return struct.unpack("<"+fmt,self.take(struct.calcsize("<"+fmt)))
    def string(self):
        n,=self.get("I")
        if n>65536:raise ValueError("NIF string limit")
        return self.take(n)

def blocks(raw):
    if len(raw)>64*1024*1024:raise ValueError("NIF size limit")
    r=Reader(raw)
    if r.take(len(MAGIC))!=MAGIC:raise ValueError("Unsupported NIF header")
    version,endian,user,n,stream=r.get("IBIII")
    if (version,endian,user,stream)!=(0x14020007,1,11,34) or not 1<=n<=10000:raise ValueError("Unsupported NIF stream")
    for _ in range(3):r.take(r.get("B")[0])
    k,=r.get("H")
    if not 1<=k<=256:raise ValueError("NIF type count")
    types=[r.string().decode("ascii") for _ in range(k)]
    indices=[r.get("H")[0] for _ in range(n)]
    if any(i>=k for i in indices):raise ValueError("Invalid block type index")
    sizes=[r.get("I")[0] for _ in range(n)]
    strings,maxlen=r.get("II")
    if strings>100000 or maxlen>65536:raise ValueError("NIF string table limit")
    for _ in range(strings):r.string()
    groups,=r.get("I")
    if groups>n:raise ValueError("NIF group count")
    r.take(groups*4)
    result=[(types[i],r.take(size)) for i,size in zip(indices,sizes)]
    roots,=r.get("I")
    if roots>n or any(not 0<=r.get("i")[0]<n for _ in range(roots)) or r.i!=len(raw):raise ValueError("Invalid NIF footer")
    return result

def decode_geometry(raw):
    r=Reader(raw);group,n,keep,compress,has=r.get("iHBBB")
    if not n or not has:raise ValueError("Missing NIF vertices")
    vertices=[r.get("3f") for _ in range(n)]
    flags,has=r.get("HB")
    if has:r.take(n*12)
    if has and flags&0x1000:r.take(n*24)
    r.take(16)
    if r.get("B")[0]:r.take(n*16)
    uv=[(u,1-v) for u,v in (r.get("2f") for _ in range(n))] if flags&1 else [(0,0)]*n
    consistency,additional,t,points,has=r.get("HiHIB")
    if not has or points!=3*t or additional!=-1:raise ValueError("Unsupported geometry layout")
    triangles=[r.get("3H") for _ in range(t)]
    if r.get("H")[0]!=0 or r.i!=len(raw):raise ValueError("Unsupported matching normal groups")
    mesh=Mesh();mesh.vertices=vertices;mesh.uv=uv;mesh.faces=[(tri,"lod") for tri in triangles]
    validate_mesh(mesh);return mesh

def check(raw,expected):
    rows=blocks(raw)
    geom=[decode_geometry(b) for t,b in rows if t=="NiTriShapeData"]
    if len(geom)!=1 or len(geom[0].faces)!=expected:raise ValueError("NIF geometry roundtrip mismatch")
    return {"triangles":expected,"vertices":len(geom[0].vertices),"block_types":[t for t,_ in rows],"runtime_verified":False}


def read_static(raw):
    """Read simple unskinned stream-34 shapes with a single diffuse/normal pair.

    Refuses unsupported transforms, shader layouts and scene graphs; never silently
    substitutes a proxy or discards a material. Returns mesh in native game units.
    """
    rows=blocks(raw)
    allowed={"NiNode","BSFadeNode","BSMultiBoundNode","NiTriShape","BSSegmentedTriShape",
             "NiTriShapeData","BSShaderPPLightingProperty","BSShaderTextureSet","BSMultiBound","BSMultiBoundAABB"}
    if any(t not in allowed for t,_ in rows):raise ValueError("Unsupported static NIF blocks")
    def ref(index,kinds):
        if not 0<=index<len(rows) or rows[index][0] not in kinds:raise ValueError("Unexpected NIF reference")
        return rows[index]
    def node_header(data):
        r=Reader(data)
        name,n=r.get("iI")
        if n:raise ValueError("Extra data unsupported")
        if r.get("i")[0]!=-1:raise ValueError("Controller unsupported")
        flags,*transform=r.get("I13f")
        if not all(isfinite(v) for v in transform):raise ValueError("Nonfinite transform")
        if transform!=[0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.,1.,1.]:raise ValueError("Nonidentity node transform")
        count,=r.get("I")
        if count>32:raise ValueError("Property limit")
        props=[r.get("i")[0] for _ in range(count)]
        if r.get("i")[0]!=-1:raise ValueError("Collision unsupported")
        return r,props
    seen=set();mesh=Mesh();materials=set()
    def visit(idx):
        if idx in seen:raise ValueError("Shared or cyclic geometry")
        seen.add(idx)
        kind,data=ref(idx,{"NiNode","BSFadeNode","BSMultiBoundNode","NiTriShape","BSSegmentedTriShape"})
        r,props=node_header(data)
        if kind in ("NiNode","BSFadeNode","BSMultiBoundNode"):
            if props:raise ValueError("Node properties unsupported")
            count,=r.get("I")
            if count>1024:raise ValueError("Child limit")
            for _ in range(count):visit(r.get("i")[0])
            if r.get("I")[0]!=0:raise ValueError("Effects unsupported")
            if kind=="BSMultiBoundNode":ref(r.get("i")[0],{"BSMultiBound"})
            if r.i!=len(data):raise ValueError("Unsupported node tail")
            return
        geom,skin,material_count,active,needs=r.get("iiIiB")
        if skin!=-1 or material_count or len(props)!=1:raise ValueError("Unsupported shape material or skin")
        if kind=="BSSegmentedTriShape":
            count,=r.get("I")
            if count>256:raise ValueError("Segment limit")
            r.take(count*9)
        if r.i!=len(data):raise ValueError("Unsupported shape tail")
        g=decode_geometry(ref(geom,{"NiTriShapeData"})[1])
        shader=Reader(ref(props[0],{"BSShaderPPLightingProperty"})[1])
        _,n,controller=shader.get("iIi")
        if n or controller!=-1:raise ValueError("Animated shader unsupported")
        shade,shader_type,f1,f2,env,clamp,tex=shader.get("HIIIfIi")
        if shader_type!=1 or f1 & ~0x82000001 or f2 & ~0x17:raise ValueError("Unsupported material flags")
        tr=Reader(ref(tex,{"BSShaderTextureSet"})[1]);n,=tr.get("I")
        if n!=6:raise ValueError("Unsupported texture set")
        paths=[tr.string().decode("ascii").replace("\\","/") for _ in range(n)]
        if tr.i!=len(tr.raw) or not paths[0] or not paths[1] or any(paths[2:]):raise ValueError("Unsupported texture set")
        materials.add(tuple(paths[:2]))
        offset=len(mesh.vertices)
        mesh.vertices.extend(g.vertices);mesh.uv.extend(g.uv)
        mesh.faces.extend((tuple(i+offset for i in f),"lod") for f,_ in g.faces)
    visit(0)
    if len(materials)!=1:raise ValueError("Multiple materials require atlas authoring")
    validate_mesh(mesh)
    return mesh,next(iter(materials))
