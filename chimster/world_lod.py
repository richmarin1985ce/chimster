"""Generate a bounded, portable LOD package directly from winning LAND records.
OBJ output is deliberately not advertised as Bethesda runtime terrain LOD.
"""
from pathlib import Path
import json, hashlib, shutil
from .lod import terrain_grid
from .flora import write_obj
from .max_height import decode_land
from .world_browser import label

def export(browser,world,output,steps=(2,4,8)):
    if world not in browser.worlds:raise ValueError("Select a worldspace")
    if not steps or len(set(steps))!=len(steps) or any(s not in (1,2,4,8,16,32) for s in steps):raise ValueError("Invalid terrain LOD steps")
    cells=[]
    for cell in browser.cells[world]:
        if "grid" not in cell:continue
        if len(browser.coordinates[world,cell["grid"]])!=1:raise ValueError("Ambiguous terrain cell")
        lands=[r for r in browser.children[cell["key"]] if r["signature"]=="LAND" and "height_raw" in r]
        if len(lands)>1:raise ValueError("Ambiguous landscape")
        if lands:cells.append((cell,lands[0]))
    if not cells or len(cells)>1024:raise ValueError("LOD export requires 1–1024 LAND cells")
    grids={c["grid"]:decode_land(l["height_raw"]) for c,l in cells}
    seams=[]
    for (x,y),h in grids.items():
        right=grids.get((x+1,y));up=grids.get((x,y+1))
        if right is not None and any(abs(a[-1]-b[0])>1e-4 for a,b in zip(h,right)):seams.append(((x,y),(x+1,y)))
        if up is not None and any(abs(a-b)>1e-4 for a,b in zip(h[-1],up[0])):seams.append(((x,y),(x,y+1)))
    out=Path(output);out.mkdir(parents=False,exist_ok=False)
    manifest={"world":label(world),"units":"game units","steps":list(steps),"seams":seams,"tiles":[],"native_runtime_assets":False}
    try:
        for cell,land in sorted(cells,key=lambda p:p[0]["grid"]):
            x,y=cell["grid"];heights=grids[x,y]
            for step in steps:
                mesh=terrain_grid(heights,step=step,spacing=128,origin=(x*4096,y*4096))
                name=f"cell_{x}_{y}_step{step}.obj"
                write_obj(mesh,out/name)
                manifest["tiles"].append({"cell":label(cell["key"]),"grid":[x,y],"step":step,"file":name,
                    "triangles":len(mesh.faces),"sha256":hashlib.sha256((out/name).read_bytes()).hexdigest()})
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    except Exception:
        shutil.rmtree(out);raise
    return manifest
