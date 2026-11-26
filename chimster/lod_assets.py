"""Intermediate asset utilities: legacy uncompressed DDS, material atlases and
conservative vertex clustering. Not a game LOD archive writer."""
from pathlib import Path
import struct,math
from .atlas import pack, remap_uv
from .flora import Mesh
from .lod import validate_mesh

def dds_rgba(width,height,rgba):
    """Single-level legacy A8R8G8B8 DDS (BGRA bytes). No compression or mipmaps."""
    if not 1<=width<=4096 or not 1<=height<=4096 or len(rgba)!=width*height*4:raise ValueError("invalid RGBA image")
    header=[124,0x100f,height,width,width*4,0,0]+[0]*11
    header += [32,0x41,0,32,0x00ff0000,0x0000ff00,0x000000ff,0xff000000]
    header += [0x1000,0,0,0,0]
    out=bytearray(rgba);out[0::4]=rgba[2::4];out[2::4]=rgba[0::4]
    return b"DDS "+struct.pack("<31I",*header)+out

def write_dds(path,width,height,rgba):
    path=Path(path)
    if path.suffix.lower()!=".dds":raise ValueError("expected DDS path")
    with path.open("xb") as f:f.write(dds_rgba(width,height,rgba))

def object_atlas(mesh,tiles,width=1024,height=1024,gutter=2,*,compatibility):
    """All supplied materials must be explicitly compatible non-tiling textures.
    Material seams are split; source geometry remains unchanged."""
    validate_mesh(mesh)
    used={m for _,m in mesh.faces}
    if {t.name for t in tiles}!=used or set(compatibility)!=used:raise ValueError("missing material mapping")
    keys=list(compatibility.values())
    if any(k.get("tiling") is not False for k in keys) or any(k!=keys[0] for k in keys[1:]):raise ValueError("incompatible shader/texture set")
    rgba,layout=pack(tiles,width,height,gutter);out=Mesh();mapping={}
    for tri,mat in mesh.faces:
        indices=[]
        for i in tri:
            k=(i,mat)
            if k not in mapping:
                mapping[k]=len(out.vertices);out.vertices.append(mesh.vertices[i])
                u,v=mesh.uv[i]
                # OBJ UV convention bottom-left; image atlas uses top-left.
                a,b=remap_uv(u,1-v,layout[mat]);out.uv.append((a,1-b))
            indices.append(mapping[k])
        out.faces.append((tuple(indices),"object_atlas"))
    return out,rgba,layout

def simplify(mesh,cell,uv_bins=64):
    """Vertex-cluster approximation; preserves separate material/UV bins.
    Rejects total collapse. Not production quadric-error simplification."""
    validate_mesh(mesh)
    if not math.isfinite(cell) or cell<=0 or not isinstance(uv_bins,int) or not 1<=uv_bins<=1024:raise ValueError("invalid clustering parameters")
    groups={};face_keys=[]
    for tri,mat in mesh.faces:
        keys=[]
        for i in tri:
            p=mesh.vertices[i];uv=mesh.uv[i]
            k=(mat,*(math.floor(v/cell) for v in p),*(round(v*uv_bins) for v in uv))
            groups.setdefault(k,set()).add(i);keys.append(k)
        face_keys.append((keys,mat))
    out=Mesh();idx={}
    for k,ids in groups.items():
        ids=sorted(ids);idx[k]=len(out.vertices)
        out.vertices.append(tuple(sum(mesh.vertices[j][a] for j in ids)/len(ids) for a in range(3)))
        out.uv.append(tuple(sum(mesh.uv[j][a] for j in ids)/len(ids) for a in range(2)))
    seen=set()
    for ks,mat in face_keys:
        tri=tuple(idx[k] for k in ks)
        if len(set(tri))<3:continue
        key=(tuple(sorted(tri)),mat)
        if key in seen:continue
        seen.add(key);out.faces.append((tri,mat))
    validate_mesh(out)
    return out
