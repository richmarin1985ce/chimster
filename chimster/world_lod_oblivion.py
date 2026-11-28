"""Oblivion distant-landscape candidate generation using native stream-11 NIFs."""
from pathlib import Path
from hashlib import sha256
import json,shutil
from .world_lod_builtin import collect,macro_mesh,textures
from .world_lod_metadata import dirty_tiles,world_bounds
from .world_lod_native import world_name
from .textures import mip_dds
from .flora import write_obj

def plan(browser,world):
    if browser.profile!="oblivion":raise ValueError("Select Oblivion worldspace")
    name=world_name(browser,world)
    sources=getattr(browser,"source_paths",None)
    if not sources or len(sources)>254:raise ValueError("Explicit full-plugin load order required")
    order={p.name.casefold():i for i,p in enumerate(sources)}
    if world.origin not in order or not 0<world.local<=0xffffff:raise ValueError("Invalid world identity")
    fid=(order[world.origin]<<24)|world.local
    grids=collect(browser,world);tiles=[]
    for x,y in dirty_tiles(grids,(32,))[32]:
        stem=f"{fid}.{x}.{y}.32"
        tiles.append({"grid":[x,y],"stem":stem,"native_mesh_target":f"meshes/landscape/lod/{stem}.nif",
                      "diffuse_target":f"textures/landscapelod/generated/{stem}.dds",
                      "normal_target":f"textures/landscapelod/generated/{stem}_fn.dds"})
    return {"world":name,"formid":fid,"load_order":list(order),"bounds":world_bounds(grids),"tiles":tiles,
            "native_runtime_assets":False,"external_tools":False,"scope":"Oblivion native terrain mesh and texture candidates; runtime unverified"},grids

def export(browser,world,output,size=128,intermediates=False):
    if size not in (64,128,256):raise ValueError("Unsupported texture dimensions")
    report,grids=plan(browser,world)
    out=Path(output);out.mkdir(exist_ok=False)
    try:
        for tile in report["tiles"]:
            x,y=tile["grid"];mesh=macro_mesh(grids,x,y,32,skirts=256,stitch=True)
            from .oblivion_lod_nif import encode,inspect
            raw=encode(mesh,tile["diffuse_target"])
            info=inspect(raw)
            if info["triangles"]!=len(mesh.faces):raise ValueError("TES4 geometry mismatch")
            dest=out/tile["native_mesh_target"];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
            written=[dest]
            if intermediates:
                obj=out/"intermediate"/(tile["stem"]+".obj");obj.parent.mkdir(exist_ok=True)
                write_obj(mesh,obj);written.append(obj)
                tile["intermediate_mesh"]=str(obj.relative_to(out))
            a,b=textures(grids,x,y,32,size)
            paths=(tile["diffuse_target"],tile["normal_target"])
            for rel,data,normal in zip(paths,(a,b),(False,True)):
                p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(mip_dds(size,size,data,normal=normal))
            tile["triangles"]=len(mesh.faces)
            tile["files"]={str(p.relative_to(out)):sha256(p.read_bytes()).hexdigest() for p in (*written,*(out/r for r in paths))}
        (out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return report
