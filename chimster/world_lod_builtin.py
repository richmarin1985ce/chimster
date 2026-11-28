"""Built-in terrain LOD generation, native NIF candidates and DDS maps.
No subprocess, third-party executable, or optional Python package.
"""
from pathlib import Path
from collections import defaultdict
from math import sqrt
from hashlib import sha256
import json,shutil
from .world_browser import label
from .world_lod_metadata import world_bounds,dirty_tiles,fnv_settings,read_fnv_settings,skyrim_settings,read_skyrim_settings
from .max_height import decode_land
from .flora import Mesh
from .textures import mip_dds
from .world_lod_materials import Baker
from .record_graph import Identity
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

def macro_mesh(grids,x,y,level,skirts=0,stitch=False):
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
                def at(u,v):return vertex(cx*32+u,cy*32+v,h[v][u])
                a,b,c,d=(at(u,v) for u,v in ((i,j),(i+step,j),(i,j+step),(i+step,j+step)))
                if stitch and step>2:
                    # Every macro boundary uses the finest LOD4 edge spacing.
                    # Refine only boundary quads, maintaining the coarse interior.
                    ring=[a]
                    if cy==y and j==0:ring.extend(at(u,j) for u in range(i+2,i+step,2))
                    ring.append(b)
                    if cx==x+level-1 and i+step==32:ring.extend(at(i+step,v) for v in range(j+2,j+step,2))
                    ring.append(d)
                    if cy==y+level-1 and j+step==32:ring.extend(at(u,j+step) for u in range(i+step-2,i,-2))
                    ring.append(c)
                    if cx==x and i==0:ring.extend(at(i,v) for v in range(j+step-2,j,-2))
                    if len(ring)>4:
                        middle=at(i+step//2,j+step//2)
                        mesh.faces.extend(((a,b,middle),"terrain") for a,b in zip(ring,ring[1:]+ring[:1]))
                        continue
                mesh.faces.extend((((a,b,c),"terrain"),((b,d,c),"terrain")))
    if not mesh.faces:raise ValueError("Empty LOD tile")
    if skirts:
        if not 0<skirts<=8192:raise ValueError("Invalid seam skirt depth")
        # Boundary edges only. Duplicated downward vertices hide mixed-tier cracks;
        # original samples, internal edges and UVs remain unchanged.
        edges={}
        for face,_ in mesh.faces:
            for a,b in zip(face,face[1:]+face[:1]):
                k=tuple(sorted((a,b)));edges[k]=None if k in edges else (a,b)
        lowered={}
        def lower(i):
            if i not in lowered:
                a,b,c=mesh.vertices[i];lowered[i]=len(mesh.vertices)
                mesh.vertices.append((a,b,c-skirts));mesh.uv.append(mesh.uv[i])
            return lowered[i]
        for edge in edges.values():
            if edge is None:continue
            a,b=edge;c,d=lower(a),lower(b)
            mesh.faces.extend((((b,a,c),"terrain"),((b,c,d),"terrain")))
    return mesh

def textures(grids,x,y,level,size=128,baker=None,materials=None):
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
            fallback=((*[round(t*shade) for t in (145,120,88)],255),(*[round((t+1)*127.5) for t in n],255))
            layers=(materials or {}).get((x+cx,y+cy))
            a,b=baker.sample(layers,(gx-cx)*32,(gy-cy)*32,(x+gx)*32,(y+gy)*32,fallback) if baker and layers else fallback
            diffuse.extend(a);normal.extend(b)
    return diffuse,normal

def export(browser,world,output,levels=LEVELS,size=128,assets=None,previous=None,skirts=256,stitch=True):
    if browser.profile not in ("new-vegas","fallout3","skyrim","skyrim-se","fallout4"):raise ValueError("Native world LAND decoder not supported for this profile")
    modern=browser.profile in ("skyrim","skyrim-se","fallout4")
    if not levels or len(set(levels))!=len(levels) or any(n not in LEVELS for n in levels):raise ValueError("Unsupported LOD tier")
    if size not in (64,128,256):raise ValueError("Unsupported texture size")
    name=world_name(browser,world);grids=collect(browser,world)
    baker=Baker(browser,assets) if assets is not None else None
    materials={};material_errors=[]
    for cell in browser.cells[world]:
        if "grid" not in cell:continue
        for land in browser.children[cell["key"]]:
            if land["signature"]!="LAND":continue
            if "land_materials" in land:materials[cell["grid"]]=land["land_materials"]
            if "land_material_error" in land:material_errors.append(land["land_material_error"])
    if baker:
        for quadrants in materials.values():
            for q in quadrants:
                for key in [q["base"]]+[a["texture"] for a in q["layers"]]:
                    if key:baker.material(key)
    origin=tuple(v//max(levels)*max(levels) for v in world_bounds(grids)["min_cell"])
    plan=dirty_tiles(grids,levels)
    tile_cells=defaultdict(list)
    for level in levels:
        for cx,cy in grids:tile_cells[(level,cx//level*level,cy//level*level)].append((cx,cy))
    # Build canonical dependency hashes once rather than serialize heights on every tier.
    cell_hashes={k:sha256(json.dumps([grids[k],materials.get(k)],sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest() for k in grids}
    texture_dependencies=[sorted(baker.hashes.items()),[(str(k),browser.active.get(Identity(*k),{}).get("texture_set")) for k in sorted(baker.layers)],[(str(k),r.get("texture_paths")) for k,r in sorted(browser.active.items()) if r["signature"]=="TXST"]] if baker else None
    old={};old_root=None
    if previous is not None:
        old_root=Path(previous).resolve(strict=True)
        prior=json.loads((old_root/"manifest.json").read_text(encoding="utf-8"))
        if prior.get("world")!=name:raise ValueError("Previous package belongs to another world")
        old={(t["level"],*t["grid"]):t for t in prior["tiles"]}
    if sum(map(len,plan.values()))>4096:raise ValueError("LOD tile budget")
    out=Path(output);out.mkdir(exist_ok=False)
    manifest={"world":name,"profile":browser.profile,"bounds":world_bounds(grids),"tiles":[],"native_runtime_assets":False,
              "external_tools":False,"texture_mode":"LAND source material blend with reported fallback" if baker else "procedural fallback; no source assets selected",
              "material_issues":material_errors,"seam_skirt_depth":skirts,"shared_fine_perimeter":stitch,"reused_tiles":0,"rebuilt_tiles":0,
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
                if modern:
                    stem=f"{name}.{level}.{x}.{y}"
                    mesh_path=f"meshes/terrain/{name}/{stem}.btr"
                    diffuse=f"textures/terrain/{name}/{stem}.dds"
                    normal=f"textures/terrain/{name}/{stem}_n.dds"
                # Include neighbor cells for edge normal/transition changes; input hashes are canonical.
                area=[((cx,cy),cell_hashes[cx,cy]) for cx in range(x-1,x+level+1) for cy in range(y-1,y+level+1) if (cx,cy) in cell_hashes]
                digest=sha256(json.dumps(["lod-v7",browser.profile,name,level,x,y,size,skirts,stitch,area,texture_dependencies],sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
                cached=old.get((level,x,y),{})
                paths=(mesh_path,diffuse,normal)
                if cached.get("input_sha256")==digest and set(cached.get("files",{}))==set(paths):
                    if all((old_root/p).is_file() and (old_root/p).resolve().is_relative_to(old_root) and sha256((old_root/p).read_bytes()).hexdigest()==cached["files"][p] for p in paths):
                        for p in paths:
                            (out/p).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old_root/p,out/p)
                        manifest["tiles"].append(cached);manifest["reused_tiles"]+=1;continue
                mesh=macro_mesh({k:grids[k] for k in tile_cells[(level,x,y)]},x,y,level,skirts,stitch)
                if modern:
                    from .modern_lod_codec import encode_groups,inspect
                    raw=encode_groups([(mesh,diffuse,normal)],browser.profile,"terrain")
                    report=inspect(raw,browser.profile)
                    if report["triangles"]!=len(mesh.faces):raise ValueError("Modern LOD geometry mismatch")
                else:
                    raw=encode(mesh,diffuse,normal,"terrain")
                    report=check(raw,len(mesh.faces))
                for path in (mesh_path,diffuse,normal):(out/path).parent.mkdir(parents=True,exist_ok=True)
                (out/mesh_path).write_bytes(raw)
                a,b=textures(grids,x,y,level,size,baker,materials)
                (out/diffuse).write_bytes(mip_dds(size,size,a));(out/normal).write_bytes(mip_dds(size,size,b,normal=True))
                manifest["rebuilt_tiles"]+=1
                manifest["tiles"].append({"level":level,"grid":[x,y],"input_sha256":digest,**report,
                    "files":{p:sha256((out/p).read_bytes()).hexdigest() for p in (mesh_path,diffuse,normal)}})
        if baker:
            manifest["material_issues"].extend(sorted(baker.issues))
            manifest["source_texture_hashes"]=baker.hashes
        settings=skyrim_settings(grids,levels,origin) if modern else fnv_settings(grids,levels)
        settings_path="LODSettings/"+name+(".lod" if modern else ".dlodsettings")
        (out/settings_path).parent.mkdir(exist_ok=True)
        (out/settings_path).write_bytes(settings)
        manifest["settings"]={"path":settings_path,**(read_skyrim_settings(settings) if modern else read_fnv_settings(settings)),"sha256":sha256(settings).hexdigest()}
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return manifest
