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

def encode(mesh,diffuse,cutout=False):
    data,_,_=geometry(mesh)
    path=texture(diffuse)
    props=(3,4,6) if cutout else (3,4)
    root=av("Chimster LOD")+pack("IiI",1,1,0)
    # No shader assigned, because the legacy geometry material has an inline bool.
    shape=av("LOD geometry",props)+pack("iiB",2,-1,0)
    material=net()+pack("14f",1,1,1,1,1,1,0,0,0,0,0,0,10,1)
    # Six texture slots, base only; normal map discovered by game naming convention.
    texturing=net()+pack("IIBiIIIB",2,6,1,5,3,2,0,0)+bytes(5)+pack("I",0)
    source=net()+pack("B",1)+string(path)+pack("iIIIBB",-1,6,1,3,1,1)
    blocks=[("NiNode",root),("NiTriShape",shape),("NiTriShapeData",data),
            ("NiMaterialProperty",material),("NiTexturingProperty",texturing),("NiSourceTexture",source)]
    if cutout:blocks.append(("NiAlphaProperty",net()+pack("HB",0x1200,128)))
    types=[t for t,b in blocks]
    header=MAGIC+pack("IBIII",0x14000005,1,11,len(blocks),11)+b"\x09Chimster\0\x01\0\x01\0"
    header+=pack("H",len(types))+b"".join(string(t) for t in types)+b"".join(pack("H",i) for i in range(len(types)))+pack("I",0)
    return header+b"".join(b for t,b in blocks)+pack("Ii",1,0)

def inspect(raw):
    """Parse the supported layout independently of the serialized block lengths."""
    r=Reader(raw)
    if r.take(len(MAGIC))!=MAGIC:raise ValueError("Not Oblivion NIF")
    version,endian,user,count,stream=r.get("IBIII")
    if (version,endian,user,stream)!=(0x14000005,1,11,11) or count not in (6,7):raise ValueError("Unsupported TES4 candidate header")
    for _ in range(3):r.take(r.get("B")[0])
    n,=r.get("H")
    expected=["NiNode","NiTriShape","NiTriShapeData","NiMaterialProperty","NiTexturingProperty","NiSourceTexture"]
    if count==7:expected.append("NiAlphaProperty")
    if n!=count or [r.string().decode("ascii") for _ in range(n)]!=expected:raise ValueError("Unexpected block types")
    if [r.get("H")[0] for _ in range(n)]!=list(range(n)) or r.get("I")[0]!=0:raise ValueError("Unexpected block mapping")
    def net_read():
        r.string()
        if r.get("Ii")!=(0,-1):raise ValueError("Unsupported extra data/controller")
    def av_read():
        net_read();flags,*transform=r.get("H13f")
        if flags!=14 or not all(isfinite(v) for v in transform):raise ValueError("Invalid transform")
        n,=r.get("I")
        if n>8:raise ValueError("Property limit")
        refs=tuple(r.get("i")[0] for _ in range(n))
        if r.get("i")[0]!=-1:raise ValueError("Unexpected collision")
        return refs
    if av_read() or r.get("IiI")!=(1,1,0):raise ValueError("Invalid root")
    if av_read()!=((3,4,6) if count==7 else (3,4)) or r.get("iiB")!=(2,-1,0):raise ValueError("Invalid shape")
    start=r.i
    _,vertices,_,_,has=r.get("iHBBB")
    if not vertices or not has:raise ValueError("Missing vertices")
    r.take(vertices*12)
    flags,normal=r.get("HB")
    if flags!=0x1001 or not normal:raise ValueError("Unexpected geometry flags")
    r.take(vertices*36+16)
    if r.get("B")[0]:raise ValueError("Unexpected colors")
    r.take(vertices*8)
    _,extra,triangles,points,has=r.get("HiHIB")
    if extra!=-1 or not has or points!=triangles*3 or not triangles:raise ValueError("Invalid triangle header")
    r.take(triangles*6)
    if r.get("H")[0]:raise ValueError("Unexpected match groups")
    mesh=decode_geometry(raw[start:r.i])
    net_read()
    if not all(isfinite(v) for v in r.get("14f")):raise ValueError("Invalid material")
    net_read()
    if r.get("IIBiIIIB")!=(2,6,1,5,3,2,0,0) or r.take(5)!=bytes(5) or r.get("I")[0]!=0:raise ValueError("Invalid texturing property")
    net_read()
    if r.get("B")[0]!=1:raise ValueError("Embedded texture unsupported")
    diffuse=r.string().decode("ascii");texture(diffuse)
    if r.get("iIIIBB")!=(-1,6,1,3,1,1):raise ValueError("Unexpected texture preferences")
    if count==7:
        net_read()
        if r.get("HB")!=(0x1200,128):raise ValueError("Unexpected alpha flags")
    if r.get("Ii")!=(1,0) or r.i!=len(raw):raise ValueError("Invalid footer")
    return {"triangles":len(mesh.faces),"vertices":len(mesh.vertices),"diffuse":diffuse,"cutout":count==7,
            "block_types":expected,"runtime_verified":False}
