"""Explicit preview material mapping keyed by native Starfield .mat names.

Texture paths refer to selected BA2 or loose sources. This is not a CDB parser.
"""
from pathlib import Path
from io import BytesIO
import json
from .compatibility_asset_lookup import normalize
from .gpu_viewport import Material,ImageMap

def key(path):
    name=normalize(path)
    if not name.startswith("materials/"):name="materials/"+name
    if not name.endswith(".mat"):raise ValueError("Expected .mat path")
    return name

class PreviewMaterials:
    def __init__(self,path,sources):
        p=Path(path)
        if p.stat().st_size>1024*1024:raise ValueError("Material map too large")
        raw=json.loads(p.read_text(encoding="utf-8"))
        if raw.get("version")!=1 or not isinstance(raw.get("materials"),dict) or len(raw["materials"])>256:raise ValueError("Invalid material map")
        self.sources=sources;self.rows={};self.cache={};self.images={};self.bytes=0
        for name,row in raw["materials"].items():
            name=key(name)
            if name in self.rows or not isinstance(row,dict):raise ValueError("Invalid material row")
            if set(row)-{"diffuse","normal","specular","tint","cutout","normal_strength","directx","spec_strength","gloss","reflectivity","metallic","roughness"}:raise ValueError("Unknown material field")
            self.rows[name]=row
    def image(self,path):
        from PIL import Image
        name=normalize(path)
        if not name.startswith("textures/") or not name.endswith(".dds"):raise ValueError("Expected textures/*.dds")
        if name not in self.images:
            raw=self.sources.read(name,32*1024*1024)
            with Image.open(BytesIO(raw)) as im:
                w,h=im.size
                if not 1<=w<=2048 or not 1<=h<=2048 or self.bytes+4*w*h>64*1024*1024:raise ValueError("Preview texture budget")
                image=ImageMap(w,h,im.convert("RGBA").tobytes()).validate()
                self.images[name]=image;self.bytes+=4*w*h
        return self.images[name]
    def __call__(self,name):
        name=key(name)
        if name not in self.rows:return None
        if name not in self.cache:
            row=dict(self.rows[name])
            for field in ("diffuse","normal","specular"):
                if row.get(field) is not None:row[field]=self.image(row[field])
            if "tint" in row:row["tint"]=tuple(row["tint"])
            # Derive legacy specular gloss for the ModernGL fallback.
            if "roughness" in row and "gloss" not in row:
                r=row["roughness"]
                if not isinstance(r,(int,float)) or not .04<=r<=1:raise ValueError("Invalid roughness")
                row["gloss"]=max(1.,min(256.,2/r**2-2))
            self.cache[name]=Material(**row).validate()
        return self.cache[name]
