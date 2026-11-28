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
    tangents=[[0.,0.,0.] for _ in verts];bitangents=[[0.,0.,0.] for _ in verts]
    for (a,b,c),_ in mesh.faces:
        normal=cross(tuple(verts[b][i]-verts[a][i] for i in range(3)),tuple(verts[c][i]-verts[a][i] for i in range(3)))
        e1=tuple(verts[b][i]-verts[a][i] for i in range(3));e2=tuple(verts[c][i]-verts[a][i] for i in range(3))
        u1=mesh.uv[b][0]-mesh.uv[a][0];v1=mesh.uv[a][1]-mesh.uv[b][1]
        u2=mesh.uv[c][0]-mesh.uv[a][0];v2=mesh.uv[a][1]-mesh.uv[c][1]
        det=u1*v2-u2*v1
        tangent=tuple((v2*e1[i]-v1*e2[i])/det for i in range(3)) if abs(det)>1e-12 else (0,0,0)
        bitangent=tuple((u1*e2[i]-u2*e1[i])/det for i in range(3)) if abs(det)>1e-12 else (0,0,0)
        for k in (a,b,c):
            for i in range(3):
                normals[k][i]+=normal[i]
                tangents[k][i]+=tangent[i]
                bitangents[k][i]+=bitangent[i]
    def unit(v):
        r=sqrt(sum(x*x for x in v));return tuple(x/r for x in v) if r else (0,0,1)
    ns=[unit(v) for v in normals];ts=[];bs=[]
    for normal,tangent,bitangent in zip(ns,tangents,bitangents):
        dot=sum(a*b for a,b in zip(normal,tangent))
        ortho=tuple(tangent[i]-normal[i]*dot for i in range(3))
        if sum(v*v for v in ortho)<1e-20:
            axis=(1,0,0) if abs(normal[0])<.9 else (0,1,0)
            ortho=cross(axis,normal)
        tangent_unit=unit(ortho);b=cross(normal,tangent_unit)
        sign=-1 if sum(x*y for x,y in zip(b,bitangent))<0 else 1
        ts.append(tangent_unit);bs.append(tuple(sign*v for v in b))
    body=pack("iHBBB",0,n,0,0,1)+b"".join(pack("3f",*v) for v in verts)
    body+=pack("HB",0x1001,1)+b"".join(pack("3f",*v) for v in ns+ts+bs)
    colors=getattr(mesh,"colors",[])
    body+=pack("4fB",*center,radius,bool(colors))+b"".join(pack("4f",*rgba) for rgba in colors)+b"".join(pack("2f",u,1-v) for u,v in mesh.uv)
    body+=pack("HiHIB",0x4000,-1,t,t*3,1)+b"".join(pack("3H",*f) for f,_ in mesh.faces)+pack("H",0)
    return body,center,tuple((b-a)/2 for a,b in zip(lo,hi))

def encode_groups(groups,kind="terrain",tile_extent=None):
    """One shape per material pair, with 16 ordered object segments when requested."""
    if kind not in ("terrain","object","companion") or not 1<=len(groups)<=128:raise ValueError("Invalid LOD groups")
    names=[b"Chimster LOD"];children=[];blocks=[None];bounds=[]
    for group in groups:
        if len(group) not in (3,4):raise ValueError("Invalid material group")
        mesh,diffuse,normal=group[:3];cutout=group[3] if len(group)==4 else False
        if type(cutout)!=bool:raise ValueError("Invalid alpha mode")
        for path in (diffuse,normal):
            if not path.isascii() or not path.lower().endswith(".dds") or not path.lower().startswith("textures/") or any(p in ("",".","..") or ":" in p for p in path.split("/")):raise ValueError("Unsafe DDS path")
        segments=None
        if kind=="object":
            if not tile_extent or tile_extent<=0:raise ValueError("Object LOD requires tile extent")
            buckets=[[] for _ in range(16)]
            for f,m in mesh.faces:
                center=tuple(sum(mesh.vertices[v][a] for v in f)/3 for a in range(2))
                x,y=(min(3,max(0,int(v/tile_extent*4))) for v in center)
                buckets[y*4+x].append((f,m))
            copied=Mesh();copied.vertices=list(mesh.vertices);copied.uv=list(mesh.uv);copied.colors=list(mesh.colors);copied.lod_alpha_threshold=getattr(mesh,"lod_alpha_threshold",128)
            copied.faces=[face for bucket in buckets for face in bucket];mesh=copied
            segments=[];offset=0
            for bucket in buckets:
                segments.append((0,offset,len(bucket)));offset+=len(bucket)*3
        data,center,extent=geometry(mesh)
        bounds.extend(tuple(center[i]+sign*extent[i] for i in range(3)) for sign in (-1,1))
        i=len(blocks);children.append(i);names.append(("LOD Geometry "+str(len(children))).encode("ascii"))
        shape=av(len(names)-1,(i+2,i+4) if cutout else (i+2,))+pack("iiIiB",i+1,-1,0,-1,0)
        shape_type="NiTriShape"
        if segments is not None:
            shape_type="BSSegmentedTriShape"
            shape+=pack("I",len(segments))+b"".join(pack("BII",*s) for s in segments)
        flag={"terrain":2,"object":4,"companion":0}[kind]
        shader=net()+pack("HIIIfIififf",1,1,0x80000100 if cutout else 0x80000000,1|flag|(32 if mesh.colors else 0),1.,0,i+3,0.,0,4.,1.)
        textures=pack("I",6)+b"".join(string(p.replace("/","\\")) for p in (diffuse,normal,"","","",""))
        blocks.extend([(shape_type,shape),("NiTriShapeData",data),("BSShaderPPLightingProperty",shader),("BSShaderTextureSet",textures)])
        if cutout:
            # NiAlphaProperty: alpha test enabled, GREATER, threshold 128; no blending.
            threshold=getattr(mesh,"lod_alpha_threshold",128)
            if type(threshold)!=int or not 0<=threshold<=255:raise ValueError("Invalid alpha threshold")
            blocks.append(("NiAlphaProperty",net()+pack("HB",0x1200,threshold)))
    lo=tuple(min(p[i] for p in bounds) for i in range(3));hi=tuple(max(p[i] for p in bounds) for i in range(3))
    center=tuple((a+b)/2 for a,b in zip(lo,hi));extent=tuple((b-a)/2 for a,b in zip(lo,hi))
    i=len(blocks)
    root=av(0)+pack("I",len(children))+b"".join(pack("i",c) for c in children)+pack("Ii",0,i)
    blocks[0]=("BSMultiBoundNode",root)
    blocks.extend([("BSMultiBound",pack("i",i+1)),("BSMultiBoundAABB",pack("6f",*center,*extent))])
    types=list(dict.fromkeys(t for t,_ in blocks))
    header=MAGIC+pack("IBIII",0x14020007,1,11,len(blocks),34)+b"\x09Chimster\0\x01\0\x01\0"
    header+=pack("H",len(types))+b"".join(string(t) for t in types)
    header+=b"".join(pack("H",types.index(t)) for t,_ in blocks)+b"".join(pack("I",len(b)) for _,b in blocks)
    header+=pack("II",len(names),max(map(len,names)))+b"".join(string(s) for s in names)+pack("I",0)
    return header+b"".join(b for _,b in blocks)+pack("Ii",1,0)

def encode(mesh,diffuse,normal,kind="terrain",segmented=False,cutout=False):
    if segmented and kind!="object":raise ValueError("Only object LOD uses segments")
    return encode_groups([(mesh,diffuse,normal,cutout)],kind,16384 if kind=="object" else None)

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
    colors=[r.get("4f") for _ in range(n)] if r.get("B")[0] else []
    uv=[(u,1-v) for u,v in (r.get("2f") for _ in range(n))] if flags&1 else [(0,0)]*n
    consistency,additional,t,points,has=r.get("HiHIB")
    if not has or points!=3*t or additional!=-1:raise ValueError("Unsupported geometry layout")
    triangles=[r.get("3H") for _ in range(t)]
    if r.get("H")[0]!=0 or r.i!=len(raw):raise ValueError("Unsupported matching normal groups")
    mesh=Mesh();mesh.vertices=vertices;mesh.uv=uv;mesh.colors=colors;mesh.faces=[(tri,"lod") for tri in triangles]
    validate_mesh(mesh);return mesh

def check(raw,expected):
    rows=blocks(raw)
    geom=[decode_geometry(b) for t,b in rows if t=="NiTriShapeData"]
    if not geom or sum(len(g.faces) for g in geom)!=expected:raise ValueError("NIF geometry roundtrip mismatch")
    return {"triangles":expected,"vertices":sum(len(g.vertices) for g in geom),"block_types":[t for t,_ in rows],"runtime_verified":False}


def read_static_groups(raw,include_cutout=False):
    """Read unskinned stream-34 shapes grouped by texture pair.

    Refuses unsupported transforms, shader layouts and scene graphs; never silently
    substitutes a proxy or discards a material. Returns mesh in native game units.
    """
    rows=blocks(raw)
    allowed={"NiNode","BSFadeNode","BSMultiBoundNode","NiTriShape","BSSegmentedTriShape",
             "NiTriShapeData","BSShaderPPLightingProperty","BSShaderTextureSet","BSMultiBound","BSMultiBoundAABB","NiAlphaProperty"}
    # Only traverse render objects. Physics and inert metadata are not copied.
    inert={"NiStringExtraData","NiIntegerExtraData","BSXFlags","BSBound","NiBinaryExtraData"}
    if any(t not in allowed and t not in inert and not t.startswith("bhk") for t,_ in rows):raise ValueError("Unsupported static NIF blocks")
    def ref(index,kinds):
        if not 0<=index<len(rows) or rows[index][0] not in kinds:raise ValueError("Unexpected NIF reference")
        return rows[index]
    def node_header(data):
        r=Reader(data)
        name,n=r.get("iI")
        if n>32:raise ValueError("Extra data limit")
        for _ in range(n):ref(r.get("i")[0],inert)
        if r.get("i")[0]!=-1:raise ValueError("Controller unsupported")
        flags,*transform=r.get("I13f")
        if not all(isfinite(v) for v in transform):raise ValueError("Nonfinite transform")
        if not 0<transform[12]<=1000:raise ValueError("Invalid node scale")
        rot=transform[3:12]
        if any(abs(sum(rot[i*3+k]*rot[j*3+k] for k in range(3))-(1 if i==j else 0))>1e-3 for i in range(3) for j in range(3)):raise ValueError("Invalid node rotation")
        det=rot[0]*(rot[4]*rot[8]-rot[5]*rot[7])-rot[1]*(rot[3]*rot[8]-rot[5]*rot[6])+rot[2]*(rot[3]*rot[7]-rot[4]*rot[6])
        if abs(det-1)>1e-3:raise ValueError("Mirrored node rotation unsupported")
        count,=r.get("I")
        if count>32:raise ValueError("Property limit")
        props=[r.get("i")[0] for _ in range(count)]
        collision,=r.get("i")
        if collision!=-1 and (not 0<=collision<len(rows) or not rows[collision][0].startswith("bhk")):raise ValueError("Unknown collision reference")
        return r,props,transform
    seen=set();groups={}
    def visit(idx,chain=()):
        if len(chain)>32:raise ValueError("Scene depth limit")
        if idx in seen:raise ValueError("Shared or cyclic geometry")
        seen.add(idx)
        kind,data=ref(idx,{"NiNode","BSFadeNode","BSMultiBoundNode","NiTriShape","BSSegmentedTriShape"})
        r,props,transform=node_header(data)
        chain=(transform,)+chain
        if kind in ("NiNode","BSFadeNode","BSMultiBoundNode"):
            if props:raise ValueError("Node properties unsupported")
            count,=r.get("I")
            if count>1024:raise ValueError("Child limit")
            for _ in range(count):visit(r.get("i")[0],chain)
            if r.get("I")[0]!=0:raise ValueError("Effects unsupported")
            if kind=="BSMultiBoundNode":ref(r.get("i")[0],{"BSMultiBound"})
            if r.i!=len(data):raise ValueError("Unsupported node tail")
            return
        geom,skin,material_count,active,needs=r.get("iiIiB")
        if skin!=-1 or material_count or not 1<=len(props)<=2:raise ValueError("Unsupported shape material or skin")
        shader_ids=[p for p in props if 0<=p<len(rows) and rows[p][0]=="BSShaderPPLightingProperty"]
        alpha_ids=[p for p in props if 0<=p<len(rows) and rows[p][0]=="NiAlphaProperty"]
        if len(shader_ids)!=1 or len(shader_ids)+len(alpha_ids)!=len(props):raise ValueError("Unsupported shape property")
        cutout=bool(alpha_ids);threshold=128
        if cutout:
            if not include_cutout:raise ValueError("Alpha-tested material needs grouped cutout reader")
            a=Reader(ref(alpha_ids[0],{"NiAlphaProperty"})[1]);_,count,controller=a.get("iIi");flags,threshold=a.get("HB")
            if count or controller!=-1 or flags&1 or flags&0x1e00!=0x1200 or a.i!=len(a.raw):raise ValueError("Unsupported alpha test layout")
        if kind=="BSSegmentedTriShape":
            count,=r.get("I")
            if count>256:raise ValueError("Segment limit")
            r.take(count*9)
        if r.i!=len(data):raise ValueError("Unsupported shape tail")
        g=decode_geometry(ref(geom,{"NiTriShapeData"})[1])
        shader=Reader(ref(shader_ids[0],{"BSShaderPPLightingProperty"})[1])
        _,n,controller=shader.get("iIi")
        if n or controller!=-1:raise ValueError("Animated shader unsupported")
        shade,shader_type,f1,f2,env,clamp,tex=shader.get("HIIIfIi")
        if shader_type!=1 or f1 & ~(0x82000001| (0x100 if cutout else 0)) or f2 & ~0x37:raise ValueError("Unsupported material flags")
        tr=Reader(ref(tex,{"BSShaderTextureSet"})[1]);n,=tr.get("I")
        if n!=6:raise ValueError("Unsupported texture set")
        paths=[tr.string().decode("ascii").replace("\\","/") for _ in range(n)]
        if tr.i!=len(tr.raw) or not paths[0] or not paths[1] or any(paths[2:]):raise ValueError("Unsupported texture set")
        material=(*paths[:2],cutout,threshold);mesh=groups.setdefault(material,Mesh());mesh.lod_alpha_threshold=threshold
        offset=len(mesh.vertices)
        if offset+len(g.vertices)>100000 or len(mesh.faces)+len(g.faces)>100000:raise ValueError("Static geometry budget")
        for vertex in g.vertices:
            for t in chain:
                vertex=tuple(t[i]+t[12]*sum(t[3+i*3+j]*vertex[j] for j in range(3)) for i in range(3))
            mesh.vertices.append(vertex)
        if g.colors or mesh.colors:
            if not mesh.colors:mesh.colors=[(1.,)*4]*offset
            mesh.colors.extend(g.colors or [(1.,)*4]*len(g.vertices))
        mesh.uv.extend(g.uv)
        mesh.faces.extend((tuple(i+offset for i in f),"lod") for f,_ in g.faces)
    visit(0)
    if not groups:raise ValueError("No supported static geometry")
    for mesh in groups.values():validate_mesh(mesh)
    return [(mesh,*paths[:3]) if include_cutout else (mesh,*paths[:2]) for paths,mesh in sorted(groups.items())]

def read_static(raw):
    groups=read_static_groups(raw)
    if len(groups)!=1:raise ValueError("Multiple materials require grouped authoring")
    mesh,diffuse,normal=groups[0]
    return mesh,(diffuse,normal)
