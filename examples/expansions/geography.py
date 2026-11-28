"""Expansion source geography: explicit acquisition, offline import and provenance.
Run with Python 3.12; rasterio, numpy, fiona, shapely, pyproj required for import.
No native plugin generation. No fabricated DEM or road fallback.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zipfile import ZipFile

SERVICE = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"
YEAR = 2025
PROJECTS = {
    "baltimore": {"game":"fallout3","bbox":[-76.75,39.18,-76.45,39.43],
                  "epsg":32618,"counties":["24510","24005","24003"],"xy_scale":0.35},
    "nautica": {"game":"fallout4","bbox":[-70.27,41.20,-69.94,41.40],
                "epsg":32619,"counties":["25019"],"xy_scale":0.70},
}
MAX_BYTES = 96 * 1024 * 1024

def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()

def write_json(p, obj):
    with p.open("x", encoding="utf-8") as f:
        json.dump(obj, f, sort_keys=True, separators=(",",":"), allow_nan=False)
        f.write("\n")

def plan(name):
    from rasterio.warp import transform_bounds
    r = PROJECTS[name]
    bounds = transform_bounds("EPSG:4326",f"EPSG:{r['epsg']}",*r["bbox"],densify_pts=21)
    # A common north-up 10 m grid; outward alignment preserves the source extent.
    x0,y0 = (math.floor(v/10)*10 for v in bounds[:2])
    x1,y1 = (math.ceil(v/10)*10 for v in bounds[2:])
    w,h = int((x1-x0)/10),int((y1-y0)/10)
    if max(w,h)>4096 or min(w,h)<1:
        raise ValueError("grid outside supported bound")
    p = {"bbox":f"{x0},{y0},{x1},{y1}","bboxSR":r["epsg"],"imageSR":r["epsg"],
         "size":f"{w},{h}","format":"tiff","pixelType":"F32",
         "interpolation":"RSP_BilinearInterpolation",
         "renderingRule":json.dumps({"rasterFunction":"None"}),"f":"image"}
    urls = {"dem.tif":SERVICE+"?"+urlencode(p)}
    for c in r["counties"]:
        filename=f"tl_{YEAR}_{c}_roads.zip"
        urls[filename]=f"https://www2.census.gov/geo/tiger/TIGER{YEAR}/ROADS/{filename}"
    return {**r,"project":name,"bounds":[x0,y0,x1,y1],"width":w,"height":h,
            "source_spacing_m":10,"tiger_year":YEAR,"urls":urls,
            "scale_status":"proposed horizontal compression, not native game units"}

def validate_dem(p, spec):
    import rasterio
    import numpy as np
    with rasterio.open(p) as d:
        if (d.count!=1 or d.width!=spec["width"] or d.height!=spec["height"]
            or d.crs is None or d.crs.to_epsg()!=spec["epsg"]
            or d.dtypes[0] not in ("float32","float64")):
            raise ValueError("unexpected raster dimensions, CRS or dtype")
        if any(abs(a-b)>0.05 for a,b in zip(d.bounds,spec["bounds"])):
            raise ValueError("unexpected raster bounds")
        if abs(d.transform.a-10)>.01 or abs(d.transform.e+10)>.01 or d.transform.b or d.transform.d:
            raise ValueError("unexpected raster spacing or orientation")
        a=d.read(1,masked=True)
        valid=~np.ma.getmaskarray(a) & np.isfinite(np.asarray(a))
        if not valid.any():
            raise ValueError("empty elevation coverage")
        vals=np.asarray(a)[valid]
        if float(vals.min()) < -500 or float(vals.max()) > 5000:
            raise ValueError("implausible elevations")
        return {"valid_samples":int(valid.sum()),"missing_samples":int(valid.size-valid.sum()),
                "min_m":float(vals.min()),"max_m":float(vals.max()),
                "nodata":None if d.nodata is None else str(d.nodata),
                "vertical_datum":"verify source product metadata; not inferred from horizontal CRS",
                "mask_warning":"valid elevations and NoData are not a shoreline or bathymetric survey"}

def validate_zip(p):
    with ZipFile(p) as z:
        infos=z.infolist()
        if len(infos)>64 or sum(i.file_size for i in infos)>512*1024*1024:
            raise ValueError("unexpected archive size")
        names=[i.filename.lower() for i in infos]
        for ext in (".shp",".shx",".dbf",".prj"):
            if sum(n.endswith(ext) for n in names)!=1:
                raise ValueError("missing or ambiguous shapefile component "+ext)
        if z.testzip() is not None:
            raise ValueError("archive CRC failure")

def acquire(name, folder):
    spec=plan(name)
    folder.mkdir(parents=True,exist_ok=True)
    for file,url in spec["urls"].items():
        p=folder/file
        if p.exists():
            # Resume only with an already-valid source file; offline import checks again.
            validate_dem(p,spec) if file=="dem.tif" else validate_zip(p)
            continue
        temp=folder/(file+".partial")
        # Claim the temporary name exclusively before cleanup responsibility begins.
        with temp.open("xb"):
            pass
        try:
            with urlopen(Request(url,headers={"User-Agent":"Chimster-Expansion-Geography/0.1"}),timeout=90) as src, temp.open("wb") as out:
                total=0
                while True:
                    chunk=src.read(1024*1024)
                    if not chunk: break
                    total+=len(chunk)
                    if total>MAX_BYTES: raise ValueError("download exceeds source limit")
                    out.write(chunk)
            validate_dem(temp,spec) if file=="dem.tif" else validate_zip(temp)
            # Exclusive publish, never overwrite a previously acquired source.
            p.hardlink_to(temp)
        finally:
            if temp.exists(): temp.unlink()
    print(json.dumps({"project":name,"sources":{f:digest(folder/f) for f in spec["urls"]}},indent=2))

def import_sources(name, source, out):
    import fiona
    from shapely.geometry import shape, box, mapping
    from shapely.ops import transform
    from pyproj import Transformer
    import rasterio
    import numpy as np
    spec=plan(name)
    dem_meta=validate_dem(source/"dem.tif",spec)
    for f in spec["urls"]:
        if f.endswith(".zip"): validate_zip(source/f)
    x0,y0,x1,y1=spec["bounds"]
    extent=box(*spec["bounds"])
    to_local=lambda x,y,z=None: ((np.asarray(x)-x0)*spec["xy_scale"],(np.asarray(y)-y0)*spec["xy_scale"])
    features=[]
    road_ids=set()
    for county in spec["counties"]:
        p=source/f"tl_{YEAR}_{county}_roads.zip"
        with fiona.open("zip://"+str(p.resolve())) as ds:
            if not ds.crs: raise ValueError("street source has no CRS")
            project=Transformer.from_crs(ds.crs,f"EPSG:{spec['epsg']}",always_xy=True).transform
            for row in ds:
                if row["geometry"] is None: continue
                geom=transform(project,shape(row["geometry"])).intersection(extent)
                if geom.is_empty: continue
                props=dict(row["properties"])
                # Geometry collections can include touch-only points; retain linear parts.
                parts=[geom] if geom.geom_type=="LineString" else list(getattr(geom,"geoms",[]))
                for i,part in enumerate(parts):
                    if part.geom_type!="LineString" or part.length<=0: continue
                    rid=f"{county}:{row.id}:{i}"
                    if rid in road_ids: raise ValueError("duplicate road segment identity")
                    road_ids.add(rid)
                    features.append({"id":rid,"name":props.get("FULLNAME") or "",
                        "mtfcc":props.get("MTFCC") or "","linearid":props.get("LINEARID"),
                        "source_length_m":part.length,"geometry":mapping(transform(to_local,part))})
    if not features: raise ValueError("no roads intersect source extent")
    # Publish only a new output folder. Source files stay untouched.
    out.mkdir(parents=True,exist_ok=False)
    with rasterio.open(source/"dem.tif") as ds:
        a=ds.read(1,masked=True)
        valid=~np.ma.getmaskarray(a) & np.isfinite(np.asarray(a))
        # Rows reversed so local +y is north; invalid heights remain explicit via mask.
        np.savez_compressed(out/"terrain-source.npz",
            elevation_m=np.where(valid,np.asarray(a),np.nan)[::-1].astype("float32"),
            valid=valid[::-1])
    write_json(out/"roads-local.json",{"schema":"chimster.local-roads.v1",
        "units":"provisional playable meters","origin_source_xy":[x0,y0],
        "xy_scale":spec["xy_scale"],"features":features,
        "warning":"centerlines only; not verified topology, bridge heights, postwar or playable roads"})
    write_json(out/"manifest.json",{"plan":spec,"dem":dem_meta,"road_segments":len(features),
        "source_hashes":{f:digest(source/f) for f in spec["urls"]},
        "terrain_origin_sample_xy":[x0+5,y0+5],"terrain_row_order":"south to north",
        "playable_sample_spacing_m":10*spec["xy_scale"],
        "vertical_scale":1,"status":"source geometry; no native game records",
        "pending":["independent shoreline mask","road deduplication and grade separation",
                   "authored postwar network","native terrain and road export"]})
    print(f"Imported {len(features)} street segments; output {out}")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("project",choices=PROJECTS)
    p.add_argument("action",choices=["plan","fetch","import"])
    p.add_argument("--source",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    if a.action=="plan": print(json.dumps(plan(a.project),indent=2))
    elif a.source is None: p.error("--source is required")
    elif a.action=="fetch": acquire(a.project,a.source)
    elif a.out is None: p.error("--out is required for import")
    else: import_sources(a.project,a.source,a.out)

if __name__=="__main__":
    main()
