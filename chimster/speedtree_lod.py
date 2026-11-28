"""Native billboard-based compatibility for classic SpeedTree assets.
No proprietary runtime; never mistake a leaf atlas for an entire tree.
"""
from math import isfinite,pi,cos,sin
from hashlib import sha256
from pathlib import Path
from .speedtree import parse,model_path,billboard_paths
from .lod_dds import decode
from .textures import mip_dds
from .flora import Mesh
from .lod import validate_mesh

def prepare(assets,model,dimensions,views=2):
    if views not in (1,2,4):raise ValueError("Invalid billboard view count")
    w,h=dimensions
    if not all(isfinite(v) and 0<v<=1e6 for v in (w,h)):raise ValueError("Valid TREE BNAM dimensions required")
    model=model_path(model);source=assets.get(model);info=parse(source)
    for path in billboard_paths(model):
        try:raw=assets.get(path)
        except FileNotFoundError:continue
        break
    else:raise ValueError("No authored whole-tree billboard; leaf maps cannot substitute")
    width,height,pixels=decode(raw)
    if not any(a>128 for a in pixels[3::4]) or not any(a<=128 for a in pixels[3::4]):raise ValueError("Billboard needs nonempty silhouette and transparent background")
    mesh=Mesh()
    for i in range(views):
        angle=pi*i/views;c,s=cos(angle),sin(angle)
        mesh.add([(-c*w/2,-s*w/2,0),(c*w/2,s*w/2,0),(c*w/2,s*w/2,h),(-c*w/2,-s*w/2,h)],[(0,0),(1,0),(1,1),(0,1)],[(0,1,2),(0,2,3)],"speedtree")
    n=len(mesh.vertices);mesh.vertices.extend(mesh.vertices[:]);mesh.uv.extend(mesh.uv[:])
    mesh.faces.extend(((c+n,b+n,a+n),m) for (a,b,c),m in mesh.faces[:])
    validate_mesh(mesh)
    digest=sha256(raw).hexdigest()
    # Preserve the original DDS unchanged; generate a neutral normal map.
    stem="textures/chimster/speedtree/"+digest
    diffuse=stem+".dds";normal=stem+"_n.dds"
    files={diffuse:raw,normal:mip_dds(4,4,bytes((128,128,255,255))*16,normal=True)}
    report={"model":model,"source_sha256":info["sha256"],"spt_complete":info["complete"],
            "first_unknown":info["unknown"],"billboard":path,"billboard_sha256":digest,
            "dimensions":[w,h],"triangles":len(mesh.faces),"mode":"authored billboard, not reconstructed SpeedTree geometry",
            "external_tools":False,"runtime_verified":False}
    return (mesh,diffuse,normal,True),files,report

def write_textures(output,files):
    for rel,raw in files.items():
        p=Path(output)/rel;p.parent.mkdir(parents=True,exist_ok=True)
        if p.exists():
            if p.read_bytes()!=raw:raise ValueError("Generated billboard file conflict")
        else:
            with p.open("xb") as f:f.write(raw)
    return {p:sha256(raw).hexdigest() for p,raw in files.items()}


def export(profile,assets,model,dimensions,output,views=2):
    import json,shutil
    if profile not in ("oblivion","fallout3","new-vegas"):raise ValueError("Legacy SpeedTree profile required")
    group,textures,report=prepare(assets,model,dimensions,views)
    mesh,diffuse,normal,_=group
    if profile=="oblivion":
        from .oblivion_lod_nif import encode,inspect
        raw=encode(mesh,diffuse,True);validation=inspect(raw)
    else:
        from .fnv_lod_nif import encode,check
        raw=encode(mesh,diffuse,normal,"companion",cutout=True);validation=check(raw,len(mesh.faces))
    if validation["triangles"]!=len(mesh.faces):raise ValueError("Native billboard geometry mismatch")
    out=Path(output);out.mkdir(exist_ok=False)
    try:
        files=write_textures(out,textures)
        suffix="_far" if profile=="oblivion" else "_lod"
        rel="meshes/chimster/speedtree/"+report["billboard_sha256"][:24]+suffix+".nif"
        p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("xb") as f:f.write(raw)
        files[rel]=sha256(raw).hexdigest()
        report.update(profile=profile,files=files,mesh=rel,native_spt_generated=False)
        (out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return report
