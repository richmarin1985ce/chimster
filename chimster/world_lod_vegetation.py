"""Self-contained procedural alpha-tested vegetation LOD companions.
Does not generate proprietary SPT or native tree-index files."""
from pathlib import Path
import json,shutil,re
from hashlib import sha256
from math import isfinite
from .flora import generate
from .lod import atlas_billboard
from .textures import mip_dds
from .texture_processing import dds
from .fnv_lod_nif import encode,check
from .lod_dds import decode

def build(recipe,output,name="Vegetation",scale=128,views=2,size=128):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",name):raise ValueError("Invalid asset name")
    if not isfinite(scale) or not 0<scale<=100000:raise ValueError("Invalid game-unit scale")
    if size not in (64,128,256) or views not in (1,2,4):raise ValueError("Unsupported billboard dimensions")
    recipe.validate()
    source=generate(recipe,0)
    mesh,rgba,side,layout=atlas_billboard(source,views,size)
    mesh.uv=[(u,1-v) for u,v in mesh.uv]
    mesh.vertices=[tuple(v*scale for v in p) for p in mesh.vertices]
    n=len(mesh.vertices);mesh.vertices.extend(mesh.vertices[:]);mesh.uv.extend(mesh.uv[:])
    mesh.faces.extend([((c+n,b+n,a+n),mat) for (a,b,c),mat in mesh.faces[:]])
    path=f"meshes/chimster/vegetation/{name}_lod.nif"
    diffuse=f"textures/chimster/vegetation/{name}_lod.dds"
    normal=f"textures/chimster/vegetation/{name}_lod_n.dds"
    raw=encode(mesh,diffuse,normal,"companion",cutout=True)
    info=check(raw,len(mesh.faces))
    if "NiAlphaProperty" not in info["block_types"]:raise ValueError("Missing alpha-test property")
    color=dds(side,side,rgba,kind="BC3",mips=True,alpha_coverage=True)
    normals=mip_dds(side,side,bytes((128,128,255,255))*(side*side),normal=True)
    if decode(color)[:2]!=(side,side):raise ValueError("Billboard DDS size mismatch")
    out=Path(output);out.mkdir(exist_ok=False)
    try:
        files={}
        for rel,data in ((path,raw),(diffuse,color),(normal,normals)):
            p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open("xb") as f:f.write(data)
            files[rel]=sha256(data).hexdigest()
        report={"recipe":vars(recipe),"name":name,"views":views,"size":side,"scale":scale,
                "source_triangles":len(source.faces),"billboard_triangles":len(mesh.faces),
                "native_tree_tiles":False,"external_tools":False,"runtime_verified":False,
                "asset_kind":"alpha-tested static billboard companion candidate",
                "files":files,"layout":layout}
        (out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return report


def build_source(profile,model,assets,output,name="Vegetation",views=2,size=128):
    """Create a source-textured, double-sided native vegetation companion.
    Native SpeedTree containers remain unsupported; no pretend SPT export.
    """
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",name):raise ValueError("Invalid asset name")
    if profile not in ("oblivion","fallout3","new-vegas","skyrim","skyrim-se","fallout4"):raise ValueError("Unsupported vegetation profile")
    from .lod_foliage_bake import source_groups,atlas_billboard as source_atlas
    source=assets.get(model);groups=source_groups(source,profile)
    mesh,rgba,normal_pixels,side,layout,hashes=source_atlas(groups,assets,views,size)
    suffix="_far" if profile=="oblivion" else "_lod"
    path=f"meshes/chimster/vegetation/{name}{suffix}.nif"
    diffuse=f"textures/chimster/vegetation/{name}{suffix}.dds"
    normal=f"textures/chimster/vegetation/{name}{suffix}_n.dds"
    if profile=="oblivion":
        from .oblivion_lod_nif import encode as legacy_encode,inspect
        raw=legacy_encode(mesh,diffuse,True);info=inspect(raw)
    elif profile in ("fallout3","new-vegas"):
        raw=encode(mesh,diffuse,normal,"companion",cutout=True);info=check(raw,len(mesh.faces))
    else:
        from .modern_lod_codec import encode_groups,inspect
        raw=encode_groups([(mesh,diffuse,normal,True)],profile,"companion");info=inspect(raw,profile)
    if info["triangles"]!=len(mesh.faces) or "NiAlphaProperty" not in info["block_types"]:raise ValueError("Vegetation roundtrip mismatch")
    color=dds(side,side,rgba,kind="BC3",mips=True,alpha_coverage=True)
    normals=mip_dds(side,side,normal_pixels,normal=True)
    out=Path(output);out.mkdir(exist_ok=False);files={}
    try:
        for rel,data in ((path,raw),(diffuse,color),(normal,normals)):
            p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
            with p.open("xb") as f:f.write(data)
            files[rel]=sha256(data).hexdigest()
        report={"profile":profile,"name":name,"source":model,"source_sha256":sha256(source).hexdigest(),
                "source_texture_hashes":hashes,"source_triangles":sum(len(m.faces) for m,*_ in groups),
                "billboard_triangles":len(mesh.faces),"views":views,"size":side,"layout":layout,"files":files,
                "normal_mode":"view-space geometric approximation, not source normal map bake",
                "runtime_verified":False,"external_tools":False,"native_tree_tiles":False}
        (out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return report
