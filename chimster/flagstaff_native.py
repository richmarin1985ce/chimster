"""Connect existing native flora packages to Flagstaff world content."""
from pathlib import Path
import json,math

def placement_content(recipe,placements,asset_root):
    root=Path(asset_root).resolve(strict=True)
    extent=recipe["extent_m"]
    statics={};refs=[];skipped=[]
    for p in placements:
        species=p["species"];variant=p["variant"]
        if species not in ("tree","shrub"):
            skipped.append(p["id"]);continue
        if type(variant) is not int or not 0<=variant<recipe["flora_variants"]:raise ValueError("Invalid variant")
        x,y=p["x"],p["y"]
        if not all(math.isfinite(v) for v in (x,y)) or not 0<=x<=extent or not 0<=y<=extent:raise ValueError("Invalid placement")
        if x==extent or y==extent:
            skipped.append(p["id"]);continue
        key=f"Flagstaff{species.title()}{variant}"
        model=f"chimster/flagstaff/{species}-{variant}/flora_lod0.nif"
        file=(root/"meshes"/model).resolve(strict=True)
        if not file.is_relative_to(root) or not file.is_file():raise ValueError("Missing native model")
        if key not in statics:
            # Conservative provisional bounds; replace with measured native mesh bounds.
            statics[key]={"id":key,"model":model,"bounds":[-512,-512,0,512,512,1024]}
        refs.append({"id":p["id"],"base":key,"x_m":x,"y_m":y,"yaw":p["rotation_degrees"],"scale":p["scale"]})
    return {"statics":list(statics.values()),"placements":refs},skipped
