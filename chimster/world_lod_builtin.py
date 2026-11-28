"""Built-in terrain LOD generation, native NIF candidates and DDS maps.
No subprocess, third-party executable, or optional Python package.
"""
from pathlib import Path
from collections import defaultdict
from math import sqrt
from hashlib import sha256
import json,shutil
from .world_browser import label
from .world_lod_metadata import world_bounds,dirty_tiles,fnv_settings,read_fnv_settings
from .max_height import decode_land
from .flora import Mesh
from .lod_assets import write_dds
from .fnv_lod_nif import encode,check
from .world_lod_native import world_name

LEVELS=(4,8,16,32)

def collect(browser,world):
    if world not in browser.worlds:raise ValueError("Select worldspace")
    grids={}
    for cell in browser.cells[world]:
        if "grid" not in cell:continue
        grid=cell["grid"]
        if len(browser.coordinates[world,grid])!=1:raise ValueError("Duplicate exterior cell")
        lands=[r for r in browser.children[cell["key"]] if r["signature"]=="LAND" and "height_raw" in r]
        if len(lands)>1:raise ValueError("Duplicate LAND")
        if lands:grids[grid]=decode_land(lands[0]["height_raw"])
    if not grids or len(grids)>4096:raise ValueError("Expected 1–4096 landscape cells")
    return grids

def macro_mesh(grids,x,y,level):
    # All neighboring macro tiles use the same world-aligned samples at a given level.
    step=level//2
    mesh=Mesh();ids={}
    def vertex(gx,gy,h):
        key=(gx,gy)
        if key in ids:
            i=ids[key]
            if abs(mesh.vertices[i][2]-h)>1e-4:raise ValueError("Mismatching shared terrain edge")
            return i
        i=len(mesh.vertices);ids[key]=i
        mesh.vertices.append(((gx-x*32)*128,(gy-y*32)*128,h))
        mesh.uv.append(((gx-x*32)/(level*32),(gy-y*32)/(level*32)))
        return i
    for (cx,cy),h in sorted(grids.items()):
        if not x<=cx<x+level or not y<=cy<y+level:continue
        for j in range(0,32,step):
            for i in range(0,32,step):
                a,b,c,d=(vertex(cx*32+u,cy*32+v,h[v][u]) for u,v in ((i,j),(i+step,j),(i,j+step),(i+step,j+step)))
                mesh.faces.extend((((a,b,c),"terrain"),((b,d,c),"terrain")))
    if not mesh.faces:raise ValueError("Empty LOD tile")
    return mesh

def textures(grids,x,y,level,size=128):
    # Procedural slope-shaded starter maps; not a bake of source LTEX/TXST materials.
    diffuse=bytearray();normal=bytearray()
    for iy in range(size):
        for ix in range(size):
            gx=(ix+.5)*level/size;gy=(size-iy-.5)*level/size
            cx,cy=int(gx),int(gy)
            h=grids.get((x+cx,y+cy))
            if h is None:diffuse.extend((0,0,0,255));normal.extend((128,128,255,255));continue
            u=min(32,max(0,round((gx-cx)*32)));v=min(32,max(0,round((gy-cy)*32)))
            dx=(h[v][min(32,u+1)]-h[v][max(0,u-1)])/256
            dy=(h[min(32,v+1)][u]-h[max(0,v-1)][u])/256
            n=(-dx,-dy,1);m=sqrt(sum(t*t for t in n));n=tuple(t/m for t in n)
            shade=max(.35,min(1, .65+.25*n[2]-.1*n[0]))
            diffuse.extend((*[round(t*shade) for t in (145,120,88)],255))
            normal.extend((*[round((t+1)*127.5) for t in n],255))
    return diffuse,normal

def export(browser,world,output,levels=LEVELS,size=128):
    if browser.profile not in ("new-vegas","fallout3"):raise ValueError("Built-in native candidate writer currently FO3/FNV only")
    if not levels or len(set(levels))!=len(levels) or any(n not in LEVELS for n in levels):raise ValueError("Unsupported LOD tier")
    if size not in (64,128,256):raise ValueError("Unsupported texture size")
    name=world_name(browser,world);grids=collect(browser,world)
    plan=dirty_tiles(grids,levels)
    if sum(map(len,plan.values()))>4096:raise ValueError("LOD tile budget")
    out=Path(output);out.mkdir(exist_ok=False)
    manifest={"world":name,"bounds":world_bounds(grids),"tiles":[],"native_runtime_assets":False,
              "external_tools":False,"texture_mode":"procedural fallback; not source texture bake",
              "settings_status":"Generated candidate; bounds and level semantics require game validation",
              "scope":"Experimental native NIF/DDS candidates; not an installable runtime package"}
    try:
        for level,tiles in sorted(plan.items()):
            for x,y in tiles:
                stem=f"{name}.level{level}.x{x}.y{y}"
                base=f"landscape/lod/{name}"
                mesh_path=f"meshes/{base}/{stem}.nif"
                diffuse=f"textures/{base}/diffuse/{stem}.dds"
                normal=f"textures/{base}/normal/{name}.n.level{level}.x{x}.y{y}.dds"
                mesh=macro_mesh(grids,x,y,level)
                raw=encode(mesh,diffuse,normal,"terrain")
                report=check(raw,len(mesh.faces))
                for path in (mesh_path,diffuse,normal):(out/path).parent.mkdir(parents=True,exist_ok=True)
                (out/mesh_path).write_bytes(raw)
                a,b=textures(grids,x,y,level,size)
                write_dds(out/diffuse,size,size,a);write_dds(out/normal,size,size,b)
                manifest["tiles"].append({"level":level,"grid":[x,y],**report,
                    "files":{p:sha256((out/p).read_bytes()).hexdigest() for p in (mesh_path,diffuse,normal)}})
        settings=fnv_settings(grids,levels)
        settings_path="LODSettings/"+name+".dlodsettings"
        (out/settings_path).parent.mkdir(exist_ok=True)
        (out/settings_path).write_bytes(settings)
        manifest["settings"]={"path":settings_path,**read_fnv_settings(settings),"sha256":sha256(settings).hexdigest()}
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return manifest
