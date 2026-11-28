"""Read-only Starfield external BSGeometry NIF subset; no native writes.

Parses sized blocks and root/child links, never searches raw bytes for paths.
Unsupported animated, skinned, embedded and other scene graph blocks fail closed.
"""
from math import isfinite
from .starfield_mesh import Reader,decode,decode_stream
from .compatibility_asset_lookup import normalize
from .flora import Mesh
from .lod import validate_mesh

def sized(r,limit=4096):
    return bytes(r.take(r.count(limit))).decode("utf-8",errors="strict")

def mesh_path(path):
    key=normalize(path)
    if not key.startswith("geometries/"):key="geometries/"+key
    if not key.endswith(".mesh"):key+=".mesh"
    return key

def blocks(data):
    r=Reader(data)
    line=b"Gamebryo File Format, Version 20.2.0.7\n"
    if bytes(r.take(len(line)))!=line:raise ValueError("Unsupported Starfield NIF header")
    version,endian,user,n,bs=r.read("<IBIII")
    if version!=0x14020007 or endian!=1 or user!=12 or bs not in (170,172,173,175) or not 1<=n<=10000:raise ValueError("Unsupported Starfield NIF version")
    r.take(r.read("<B")[0]);r.take(4);r.take(r.read("<B")[0]);r.take(r.read("<B")[0])
    nt,=r.read("<H")
    if not 1<=nt<=1024:raise ValueError("NIF block type count")
    kinds=[sized(r,128) for _ in range(nt)]
    indices=r.read("<"+"H"*n)
    sizes=r.read("<"+"I"*n)
    if any(i>=nt for i in indices):raise ValueError("Invalid block type index")
    ns=r.count(100000);maxlen=r.count(65536)
    strings=[sized(r,maxlen) for _ in range(ns)]
    r.take(r.count(10000)*4)
    rows=[(kinds[i],bytes(r.take(size))) for i,size in zip(indices,sizes)]
    roots=r.read("<"+"i"*r.count(n))
    if r.pos!=len(r.data) or any(i<0 or i>=n for i in roots):raise ValueError("Invalid NIF footer")
    return rows,roots,strings

def av(r):
    r.take(4);r.take(r.count(10000)*4)
    controller,flags=r.read("<iI")
    if controller!=-1:raise ValueError("Animated NIF object")
    values=r.read("<13f");r.take(4)
    if not all(isfinite(x) for x in values) or not 0<values[-1]<=1e5:raise ValueError("Invalid NIF transform")
    return flags,values

def geometry(data,units=1.,bind_pose=False):
    rows,roots,strings=blocks(data);out=[];active=set()
    def visit(index,chain,depth):
        if depth>32 or index in active or not 0<=index<len(rows):raise ValueError("Cyclic/invalid NIF scene graph")
        active.add(index);kind,raw=rows[index];r=Reader(raw)
        flags,transform=av(r);chain=(transform,)+chain
        if kind in ("NiNode","BSFadeNode","BSLeafAnimNode","CsNiNode","BSOrderedNode","BSMultiBoundNode","NiSwitchNode","NiLODNode","BSRangeNode","BSBlastNode","BSDamageStage"):
            children=r.read("<"+"i"*r.count(10000))
            if kind=="BSOrderedNode":r.take(17)
            elif kind=="BSMultiBoundNode":r.take(8)
            elif kind in ("NiSwitchNode","NiLODNode"):
                switch,index=r.read("<HI")
                if kind=="NiLODNode":r.take(4)
                if index>=len(children):raise ValueError("Invalid active NIF child")
                children=children[index:index+1]
            elif kind in ("BSRangeNode","BSBlastNode","BSDamageStage"):r.take(3)
            for child in children:
                if child!=-1:visit(child,chain,depth+1)
        elif kind=="BSGeometry":
            r.take(40);skin,shader,alpha=r.read("<3i")
            if skin!=-1 and not bind_pose:raise ValueError("Skinned BSGeometry requires explicit bind-pose preview")
            entries=[]
            for _ in range(4):
                has,=r.read("<B")
                if has not in (0,1):raise ValueError("Invalid BSGeometry mesh flag")
                if has:
                    indices,verts,meshflags=r.read("<3I")
                    if indices%3 or not verts or verts>65536:raise ValueError("Invalid BSGeometry mesh counts")
                    if flags&512:
                        decoded=decode_stream(r,units,embedded=True,bind_pose=bind_pose)
                        entries.append((decoded,indices,verts))
                    else:entries.append((mesh_path(sized(r)),indices,verts))
                else:entries.append(None)
            if not entries[0]:raise ValueError("Missing base BSGeometry mesh")
            material=None
            if 0<=shader<len(rows) and rows[shader][0]=="BSLightingShaderProperty":
                idx,=Reader(rows[shader][1]).read("<I")
                if idx<len(strings) and strings[idx].casefold().endswith(".mat"):
                    from .starfield_materials import key
                    material=key(strings[idx])
            out.append((chain,entries,material))
            if len(out)>256:raise ValueError("NIF shape limit")
        else:raise ValueError("Unsupported NIF scene node: "+kind)
        if r.pos!=len(r.data):raise ValueError("Unsupported trailing NIF block data")
        active.remove(index)
    for root in roots:visit(root,(),0)
    if not out:raise ValueError("No external static geometry")
    return out

def transformed(mesh,chain,units):
    verts=[]
    for p in mesh.vertices:
        p=tuple(p)
        for x in chain:
            p=tuple(x[i]/units+x[12]*sum(x[3+3*i+j]*p[j] for j in range(3)) for i in range(3))
        if not all(isfinite(v) and abs(v)<=1e7 for v in p):raise ValueError("NIF transform exceeds bounds")
        verts.append(p)
    return Mesh(verts,list(mesh.uv),list(mesh.faces))

def join(meshes):
    result=Mesh()
    for mesh in meshes:
        offset=len(result.vertices);result.vertices.extend(mesh.vertices);result.uv.extend(mesh.uv)
        result.faces.extend((tuple(i+offset for i in tri),mat) for tri,mat in mesh.faces)
        if len(result.vertices)>300000 or len(result.faces)>300000:raise ValueError("NIF geometry budget")
    validate_mesh(result);return result

class AutoMeshes:
    def __init__(self,sources,units=1.,fallback=None,materials=None,bind_pose=False):
        self.sources=sources;self.units=units;self.fallback=fallback;self.cache={};self.vertices=0;self.material_source=materials;self.materials={};self.material_issues=[];self.bind_pose=bind_pose
    def __call__(self,model):
        key=normalize(model)
        if not key.startswith("meshes/"):key="meshes/"+key
        if not key.endswith(".nif"):raise ValueError("Expected NIF model")
        if key in self.cache:return self.cache[key]
        if len(self.cache)>=64:raise ValueError("NIF cache limit")
        try:shapes=geometry(self.sources.read(key),self.units,self.bind_pose)
        except (ValueError,OSError,UnicodeError):
            if self.fallback is not None:return self.fallback(model)
            raise
        levels=[[],[],[],[]];has=[False]*4
        for chain,entries,material in shapes:
            if material and self.material_source is not None and material not in self.materials:
                try:
                    value=self.material_source(material)
                    if value is not None:self.materials[material]=value
                except (ValueError,OSError,TypeError,ImportError) as exc:
                    self.material_issues.append(material+": "+str(exc)[:120])
            previous=None
            for i,entry in enumerate(entries):
                if entry:
                    path,ni,nv=entry
                    m,lods,meta=decode(self.sources.read(path),self.units,self.bind_pose) if isinstance(path,str) else path
                    if len(m.vertices)!=nv or meta["indices"]!=ni:raise ValueError("BSGeometry external counts mismatch")
                    previous=transformed(m,chain,self.units);has[i]=True
                    if material:previous.faces=[(tri,material) for tri,_ in previous.faces]
                elif i==0:raise ValueError("Missing base geometry")
                levels[i].append(previous)
        last=max(i for i,on in enumerate(has) if on)
        combined=[join(level) for level in levels[:last+1]]
        count=sum(len(m.vertices) for m in combined)
        if self.vertices+count>300000:raise ValueError("Total native NIF geometry budget")
        self.vertices+=count;result=(combined[0],combined[1:]);self.cache[key]=result
        return result
