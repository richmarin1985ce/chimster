"""Bounded independent reader for Starfield external static .mesh geometry.

Positions are signed normalized 16-bit triples, UVs are half floats, and
indices are unsigned 16-bit. Attribute streams not consumed by the portable
renderer are structurally checked, not silently interpreted as materials.
"""
from pathlib import Path
from math import isfinite
import json,struct
from .flora import Mesh
from .lod import validate_mesh

MAX_BYTES=32*1024*1024
MAX_TRIANGLES=300000

class Reader:
    def __init__(self,data):
        if len(data)>MAX_BYTES:raise ValueError("Mesh size limit")
        self.data=memoryview(data);self.pos=0
    def take(self,n):
        if n<0 or self.pos+n>len(self.data):raise ValueError("Truncated Starfield mesh")
        out=self.data[self.pos:self.pos+n];self.pos+=n
        return out
    def read(self,fmt):
        return struct.unpack(fmt,self.take(struct.calcsize(fmt)))
    def count(self,limit):
        n,=self.read("<I")
        if n>limit:raise ValueError("Mesh count exceeds limit")
        return n
    def indices(self):
        n=self.count(MAX_TRIANGLES*3)
        if n%3:raise ValueError("Triangle index count is not divisible by three")
        return list(struct.iter_unpack("<3H",self.take(n*2)))

def decode_stream(r,units=1.,embedded=False,bind_pose=False):
    if not isfinite(units) or not .001<=units<=10000:raise ValueError("Invalid preview scale")
    version,=r.read("<I")
    if version not in (0,1,2):raise ValueError("Unsupported Starfield mesh version")
    triangles=r.indices()
    scale,=r.read("<f")
    if not isfinite(scale) or not 0<scale/units<=1e7:raise ValueError("Invalid mesh position scale")
    weights=r.count(16)
    n=r.count(65536)
    if not n:raise ValueError("Empty Starfield mesh")
    xyz=[tuple(x*scale/(32767.*units) for x in p) for p in struct.iter_unpack("<3h",r.take(n*6))]
    uvn=r.count(n)
    if uvn not in (0,n):raise ValueError("Invalid primary UV stream")
    uv=[(u,1-v) for u,v in struct.iter_unpack("<2e",r.take(uvn*4))] if uvn else [(0.,0.)]*n
    # Secondary UV, colors, normals and tangent streams have four bytes each.
    for stream in ("uv2","colors","normals","tangents"):
        k=r.count(n)
        if k not in (0,n):raise ValueError("Invalid "+stream+" stream")
        r.take(k*4)
    wn=r.count(n*16)
    if bool(wn)!=bool(weights) or wn!=n*weights:raise ValueError("Invalid bone weight stream")
    if wn and not bind_pose:raise ValueError("Skinned external meshes require explicit bind-pose preview")
    r.take(wn*4)
    lods=[r.indices() for _ in range(r.count(16))] if version else []
    def build(faces):
        if any(max(tri)>=n for tri in faces):raise ValueError("Out-of-range Starfield vertex index")
        m=Mesh(list(xyz),list(uv),[(tuple(t),"starfield_mesh") for t in faces if len(set(t))==3])
        validate_mesh(m);return m
    main=build(triangles)
    variants=[build(faces) for faces in lods[:3] if faces]
    for faces in lods[3:]:
        if any(max(tri)>=n for tri in faces):raise ValueError("Invalid additional LOD index")
    # Embedded BSMeshData always has meshlet and cull arrays. External
    # variants may omit the footer. Validate its extent when present.
    meshlets=0
    if embedded or r.pos<len(r.data):
        meshlets=r.count(MAX_TRIANGLES)
        r.take(meshlets*16)
        cull=r.count(MAX_TRIANGLES)
        if cull not in (0,meshlets):raise ValueError("Invalid meshlet cull count")
        r.take(cull*24)
    return main,variants,dict(version=version,vertices=n,triangles=len(main.faces),indices=len(triangles)*3,lods=len(variants),meshlets=meshlets,weights_per_vertex=weights,bind_pose=bool(wn))

def decode(data,units=1.,bind_pose=False):
    r=Reader(data);result=decode_stream(r,units,bind_pose=bind_pose)
    if r.pos!=len(r.data):raise ValueError("Unexpected trailing mesh bytes")
    return result

def load(path,units=1.):
    p=Path(path)
    if p.suffix.casefold()!=".mesh" or p.stat().st_size>MAX_BYTES:raise ValueError("Expected bounded Starfield .mesh")
    return decode(p.read_bytes(),units)

class MappedMeshes:
    """Explicit NIF-to-external-mesh manifest; no guessing NIF geometry hashes."""
    def __init__(self,path,units=1.,sources=None):
        p=Path(path).resolve(strict=True)
        if p.stat().st_size>1024*1024:raise ValueError("Mesh manifest too large")
        data=json.loads(p.read_text(encoding="utf-8"))
        if data.get("version")!=1 or not isinstance(data.get("models"),dict) or len(data["models"])>256:raise ValueError("Invalid mesh manifest")
        self.root=p.parent;self.units=units;self.sources=sources;self.paths={};self.cache={};self.vertices=0
        for model,value in data["models"].items():
            key=self.key(model)
            if not isinstance(value,str):raise ValueError("Expected relative .mesh path")
            parts=value.replace("\\","/").split("/")
            if any(not x or x in (".","..") or ":" in x or "\0" in x for x in parts):raise ValueError("Unsafe mesh path")
            dest="/".join(parts) if sources is not None else self.root.joinpath(*parts).resolve(strict=True)
            if sources is not None:
                if not dest.casefold().startswith("geometries/") or not dest.casefold().endswith(".mesh"):raise ValueError("Expected geometries/*.mesh asset")
            elif not dest.is_relative_to(self.root) or dest.suffix.casefold()!=".mesh":raise ValueError("Mesh path outside manifest directory")
            if key in self.paths:raise ValueError("Duplicate model key")
            self.paths[key]=dest
    @staticmethod
    def key(model):
        if not isinstance(model,str):raise ValueError("Invalid model path")
        key=model.replace("\\","/").casefold()
        if key.startswith("meshes/"):key=key[7:]
        if not key.endswith(".nif") or any(not x or x in (".","..") or ":" in x or "\0" in x for x in key.split("/")):raise ValueError("Expected relative NIF path")
        return key
    def __call__(self,model):
        key=self.key(model)
        if key not in self.paths:return None
        if key not in self.cache:
            if len(self.cache)>=64:raise ValueError("Mesh cache limit")
            m,lods,_=decode(self.sources.read(self.paths[key]),self.units) if self.sources is not None else load(self.paths[key],self.units)
            count=sum(len(x.vertices) for x in (m,*lods))
            if self.vertices+count>300000:raise ValueError("Combined mesh vertex budget exceeded")
            self.vertices+=count;self.cache[key]=(m,lods)
        return self.cache[key]
