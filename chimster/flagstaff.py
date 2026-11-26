"""Reproducible text/DEM-driven Flagstaff demo. Original code and generated assets.
Optional rasterio/numpy are used only for geospatial source import."""
from pathlib import Path
from math import atan,degrees,hypot,isfinite
from hashlib import sha256
from random import Random
from urllib.parse import urlencode
from urllib.request import urlopen,Request
import json,struct,html
from .lod import terrain_grid,build_tree,tile_groups,build_key
from .flora import Recipe,write_obj
from .atlas import write_png

SERVICE="https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
COLORS={"forest_candidate":(68,99,70,255),"highland_candidate":(116,128,103,255),
        "scrub_candidate":(158,136,91,255),"rock_candidate":(111,105,99,255)}

def load_recipe(path):
    r=json.loads(Path(path).read_text(encoding="utf-8"))
    n=r["samples"];extent=r["extent_m"]
    if n not in (33,65,129,257,513) or not 100<=extent<=50000 or r["epsg"]!=32612 or r["vertical_exaggeration"]!=1:
        raise ValueError("unsupported grid, extent, CRS or terrain exaggeration")
    if not all(isinstance(s,int) and s>0 and (n-1)%s==0 for s in r["terrain_lod_steps"]):raise ValueError("LOD steps must divide grid intervals")
    if not 1<=r["placement_stride"]<=32 or not 1<=r["flora_variants"]<=16:raise ValueError("invalid placement settings")
    if r["target_game"]!="newvegas":raise ValueError("demo targets New Vegas")
    return r

def dem_request(recipe):
    from rasterio.warp import transform
    c=recipe["center_wgs84"]
    x,y=transform("EPSG:4326","EPSG:32612",[c["longitude"]],[c["latitude"]])
    n=recipe["samples"]; half=recipe["extent_m"]/2
    # Sample centers span exactly extent_m. Request outer pixel edges.
    half+=recipe["extent_m"]/(n-1)/2
    bbox=[x[0]-half,y[0]-half,x[0]+half,y[0]+half]
    params={"bbox":",".join(f"{v:.6f}" for v in bbox),"bboxSR":32612,"imageSR":32612,
            "size":f"{n},{n}","format":"tiff","pixelType":"F32","interpolation":"RSP_BilinearInterpolation",
            "renderingRule":json.dumps({"rasterFunction":"None"}),"f":"image"}
    return SERVICE+"?"+urlencode(params)

def fetch_dem(recipe,output):
    p=Path(output);url=dem_request(recipe)
    if p.exists():raise FileExistsError(p)
    with urlopen(Request(url,headers={"User-Agent":"Chimster-Flagstaff-Demo/0.1"}),timeout=90) as response:
        data=response.read(32*1024*1024+1)
    if len(data)>32*1024*1024 or data[:4] not in (b"II*\0",b"MM\0*"):raise ValueError("USGS did not return bounded TIFF data")
    with p.open("xb") as f:f.write(data)
    try:
        _,metadata=read_dem(recipe,p)
    except Exception:
        p.unlink();raise
    return {"source_url":url,**metadata}

def read_dem(recipe,path):
    import rasterio
    import numpy as np
    p=Path(path)
    with rasterio.open(p) as ds:
        n=recipe["samples"]
        if ds.count!=1 or ds.width!=n or ds.height!=n or ds.crs is None or ds.crs.to_epsg()!=recipe["epsg"]:raise ValueError("unexpected DEM dimensions/CRS")
        if ds.dtypes[0] not in ("float32","float64"):raise ValueError("DEM must contain floating point elevations")
        expected=recipe["extent_m"]/(n-1)
        if abs(ds.transform.a-expected)>expected*.005 or abs(ds.transform.e+expected)>expected*.005 or ds.transform.b or ds.transform.d:raise ValueError("unexpected DEM orientation or spacing")
        from rasterio.warp import transform
        c=recipe["center_wgs84"];cx,cy=transform("EPSG:4326","EPSG:32612",[c["longitude"]],[c["latitude"]])
        center=ds.transform*(n/2,n/2)
        if hypot(center[0]-cx[0],center[1]-cy[0])>expected:raise ValueError("DEM center does not match recipe")
        a=ds.read(1,masked=True)
        if np.any(np.ma.getmaskarray(a)) or not np.all(np.isfinite(a)) or np.min(a)<0 or np.max(a)>5000:raise ValueError("invalid/NoData Flagstaff elevations")
        # GeoTIFF rows run north to south; world y increases north.
        grid=np.asarray(a,dtype=float)[::-1].tolist()
        meta={"source_file":p.name,"sha256":sha256(p.read_bytes()).hexdigest(),"epsg":recipe["epsg"],
              "affine":list(ds.transform)[:6],"bounds":list(ds.bounds),"sample_spacing_m":expected,
              "minimum_m":float(a.min()),"maximum_m":float(a.max()),"source":"USGS 3DEP if retrieved through fetch_dem"}
    return grid,meta

def regions_and_placements(grid,r):
    n=len(grid);spacing=r["extent_m"]/(n-1);rules=r["region_rules"];rng=Random(r["seed"])
    regions=[];placements=[]
    for y in range(n):
        row=[]
        for x in range(n):
            dx=(grid[y][min(x+1,n-1)]-grid[y][max(x-1,0)])/(spacing*(2 if 0<x<n-1 else 1))
            dy=(grid[min(y+1,n-1)][x]-grid[max(y-1,0)][x])/(spacing*(2 if 0<y<n-1 else 1))
            slope=degrees(atan(hypot(dx,dy)));z=grid[y][x]
            kind=("rock_candidate" if slope>=rules["rock_min_slope_degrees"] else
                  "highland_candidate" if z>=rules["highland_min_elevation_m"] else
                  "forest_candidate" if z>=rules["forest_min_elevation_m"] else "scrub_candidate")
            row.append(kind)
            if x%r["placement_stride"] or y%r["placement_stride"]:continue
            p=rules["forest_probability"] if kind=="forest_candidate" else rules["scrub_probability"] if kind in ("scrub_candidate","highland_candidate") else rules["rock_probability"]
            if rng.random()<p:
                species="tree" if kind=="forest_candidate" else "shrub" if kind!="rock_candidate" else "rock_placeholder"
                i=len(placements);variant=rng.randrange(r["flora_variants"])
                placements.append({"id":f"placement_{i:06d}","x":x*spacing,"y":y*spacing,"z_m":z,
                    "kind":"tree" if species=="tree" else "object","species":species,"variant":variant,
                    "rotation_degrees":round(rng.random()*360,3),"scale":round(rng.uniform(.75,1.25),3),
                    "material_set":"bark-leaves" if species=="tree" else "scrub" if species=="shrub" else "rock-placeholder"})
        regions.append(row)
    return regions,placements

def dump(path,value):
    Path(path).write_text(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8")

def preview_html(grid,regions,placements,recipe,out):
    # Standalone interactive map generated solely from the DEM and recipe.
    n=len(grid);skip=max(1,(n-1)//128)
    data={"n":len(grid[::skip]),"h":[row[::skip] for row in grid[::skip]],"regions":[row[::skip] for row in regions[::skip]],
          "placements":placements,"extent":recipe["extent_m"],"colors":COLORS}
    payload=json.dumps(data,separators=(",",":"),allow_nan=False).replace("<","\\u003c")
    title=html.escape(recipe["title"])
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>'''+title+'''</title><style>body{background:#171b20;color:#e4e8de;font:15px system-ui;margin:24px}canvas{max-width:100%;height:auto;background:#14191e;border:1px solid #57634f}button,label{margin:8px}p{max-width:800px;color:#b4bfae}select{padding:7px}</style>
<h1>'''+title+'''</h1><p>Chimster DEM preview — provisional geographic test area. Terrain is real when built from USGS data; vegetation is an illustrative procedural proposal, not a historical land-cover map or playable Fallout mod.</p>
<label>View <select id="mode"><option value="height">Shaded elevation</option><option value="regions">Candidate regions</option><option value="mesh">Terrain mesh (isometric)</option></select></label><label><input type="checkbox" id="trees" checked>Placements</label><label>LOD <select id="lod"><option>1</option><option>2</option><option>4</option><option>8</option></select></label>
<div><canvas id="map" width="960" height="720"></canvas></div><p id="info"></p>
<script>const D='''+payload+''';const C=document.getElementById("map"),g=C.getContext("2d"),M=document.getElementById("mode"),T=document.getElementById("trees"),L=document.getElementById("lod");
const all=D.h.flat(),lo=Math.min(...all),hi=Math.max(...all),span=Math.max(1,hi-lo);
function draw(){g.fillStyle="#14191e";g.fillRect(0,0,C.width,C.height);const step=Number(L.value),n=D.n,cell=640/(n-1),iso=M.value==="mesh";function project(x,y,z){return [480+(x-y)*2.7,360+(x+y-n+1)*1.25-(z-lo)/span*100]} 
if(iso){for(let y=n-1-step;y>=0;y-=step)for(let x=0;x<n-1;x+=step){let pts=[[x,y],[x+step,y],[x+step,y+step],[x,y+step]],z=D.h[y][x],a=Math.round(75+120*(z-lo)/span);g.fillStyle="rgb("+a+","+Math.round(a*.95)+","+Math.round(a*.78)+")";g.beginPath();pts.forEach(([u,v],i)=>{let p=project(u,v,D.h[v][u]);i?g.lineTo(...p):g.moveTo(...p)});g.closePath();g.fill();g.strokeStyle="#29352b";g.lineWidth=.35;g.stroke()}}
else {for(let y=0;y<n;y+=step)for(let x=0;x<n;x+=step){let z=D.h[y][x],shade=Math.max(.55,Math.min(1.25,1+(z-D.h[Math.max(0,y-step)][Math.max(0,x-step)])/80)),c=M.value==="regions"?D.colors[D.regions[y][x]]:[90+130*(z-lo)/span,103+120*(z-lo)/span,85+115*(z-lo)/span];g.fillStyle="rgb("+c.slice(0,3).map(v=>Math.min(255,Math.round(v*shade))).join(",")+")";g.fillRect(160+x*cell,40+(n-1-y)*cell,cell*step+1,cell*step+1)}
if(T.checked){g.fillStyle="#e8e6b2";for(const p of D.placements){g.fillRect(160+p.x/D.extent*640,40+(1-p.y/D.extent)*640,1.8,1.8)}}}
document.getElementById("info").textContent="Elevation: "+lo.toFixed(1)+"–"+hi.toFixed(1)+" m | Candidate placements: "+D.placements.length+" | preview stride "+step;}
[M,T,L].forEach(e=>e.addEventListener("change",draw));draw();</script></html>'''
    Path(out).write_text(page,encoding="utf-8")

def build(recipe,grid,metadata,output):
    n=recipe["samples"]
    if len(grid)!=n or any(len(row)!=n for row in grid) or any(not isfinite(z) for row in grid for z in row):raise ValueError("invalid terrain grid")
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    lo=min(min(row) for row in grid);hi=max(max(row) for row in grid)
    spacing=recipe["extent_m"]/(n-1)
    # Preserve original elevation values; local mesh Z subtracts a constant datum only.
    local=[[z-lo for z in row] for row in grid]
    dump(out/"elevation-meters.json",grid);dump(out/"recipe.json",recipe)
    lods=[]
    for step in recipe["terrain_lod_steps"]:
        m=terrain_grid(local,step,spacing);name=f"terrain-step{step}.obj";write_obj(m,out/name)
        lods.append({"step":step,"file":name,**m.stats()})
    regions,placements=regions_and_placements(grid,recipe)
    dump(out/"regions.json",regions);dump(out/"placements.json",placements)
    dump(out/"lod-tiles.json",tile_groups(placements,512))
    pixels=bytes(c for row in reversed(regions) for kind in row for c in COLORS[kind])
    write_png(out/"region-candidates.png",n,n,pixels)
    for species in ("tree","shrub"):
        for i in range(recipe["flora_variants"]):
            r=Recipe(species=species,seed=recipe["seed"]+i,height=8 if species=="tree" else 1.2,radius=.22 if species=="tree" else .06,branches=24 if species=="tree" else 10,leaves=240 if species=="tree" else 70)
            build_tree(r,out/"flora"/f"{species}-{i}",recipe["billboard_size"])
    preview_html(grid,regions,placements,recipe,out/"preview.html")
    report={"title":recipe["title"],"target_game":"newvegas","source":metadata,"build_key":build_key({"recipe":recipe,"grid":grid}),
        "elevation_m":{"min":lo,"max":hi,"local_z_datum":lo},"sample_spacing_m":spacing,"terrain_lods":lods,
        "placement_count":len(placements),"region_status":"heuristic candidates only; no observed land cover, geology or road data",
        "status":"Chimster-generated preview and intermediate assets; no FNV ESP, native New Vegas NIF, GECK RAW, navmesh or gameplay"}
    dump(out/"manifest.json",report)
    return report
