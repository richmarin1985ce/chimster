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
        if path is None:raw={"version":1,"materials":{}}
        else:
            p=Path(path)
            if p.stat().st_size>1024*1024:raise ValueError("Material map too large")
            raw=json.loads(p.read_text(encoding="utf-8"))
        if raw.get("version")!=1 or not isinstance(raw.get("materials"),dict) or len(raw["materials"])>256:raise ValueError("Invalid material map")
        self.sources=sources;self.rows={};self.cache={};self.images={};self.bytes=0
        for name,row in raw["materials"].items():
            name=key(name)
            if name in self.rows or not isinstance(row,dict):raise ValueError("Invalid material row")
            if set(row)-{"diffuse","normal","specular","tint","cutout","normal_strength","directx","spec_strength","gloss","reflectivity","metallic","roughness","opacity_map","roughness_map","metallic_map"}:raise ValueError("Unknown material field")
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
            opacity=row.pop("opacity_map",None)
            if opacity:
                mask=self.image(opacity)
                base=row.get("diffuse")
                # Preserve the diffuse RGB and multiply existing alpha by the
                # single-channel opacity texture using nearest resampling.
                w,h=(base.width,base.height) if base else (mask.width,mask.height)
                if self.bytes+4*w*h>64*1024*1024:raise ValueError("Preview texture budget")
                rgba=bytearray(base.rgba if base else bytes((255,255,255,255))*w*h)
                for y in range(h):
                    for x in range(w):
                        a=4*(y*w+x)+3
                        b=4*((y*mask.height//h)*mask.width+x*mask.width//w)
                        rgba[a]=(rgba[a]*mask.rgba[b]+127)//255
                row["diffuse"]=ImageMap(w,h,bytes(rgba));self.bytes+=4*w*h
            # The current portable shaders have scalar metalness/roughness,
            # not per-pixel inputs. Use mean red channel only as a preview.
            for field in ("roughness","metallic"):
                texture=row.pop(field+"_map",None)
                if texture and field not in row:
                    image=self.image(texture)
                    mean=sum(image.rgba[0::4])/(255*image.width*image.height)
                    row[field]=max(.04,mean) if field=="roughness" else mean
            if "tint" in row:row["tint"]=tuple(row["tint"])
            # Derive legacy specular gloss for the ModernGL fallback.
            if "roughness" in row and "gloss" not in row:
                r=row["roughness"]
                if not isinstance(r,(int,float)) or not .04<=r<=1:raise ValueError("Invalid roughness")
                row["gloss"]=max(1.,min(256.,2/r**2-2))
            self.cache[name]=Material(**row).validate()
        return self.cache[name]

def native_row(raw):
    """Resolve explicit first-layer JSON material components; no guessed inheritance."""
    from math import isfinite
    if len(raw)>2*1024*1024:raise ValueError("Native MAT exceeds preview limit")
    doc=json.loads(raw.decode("utf-8-sig"))
    if not isinstance(doc,dict) or doc.get("Version")!=1 or not isinstance(doc.get("Objects"),list) or not 1<=len(doc["Objects"])<=512:raise ValueError("Unsupported native MAT JSON structure")
    objects={}
    for obj in doc["Objects"]:
        if not isinstance(obj,dict):raise ValueError("Invalid native MAT object")
        ident=obj.get("ID","<this>")
        if not isinstance(ident,str) or ident in objects:raise ValueError("Ambiguous native MAT ID")
        components={}
        for comp in obj.get("Components",[]):
            if not isinstance(comp,dict) or not isinstance(comp.get("Type"),str) or not isinstance(comp.get("Data"),dict):raise ValueError("Invalid MAT component")
            index=comp.get("Index",0)
            if type(index) is not int or not 0<=index<65536:raise ValueError("Invalid MAT component index")
            k=(comp["Type"],index)
            if k in components:raise ValueError("Duplicate MAT component")
            components[k]=comp["Data"]
            if len(components)>1024:raise ValueError("MAT component budget")
        objects[ident]=components
    def get(obj,name,index=0):
        return objects[obj].get(("BSMaterial::"+name,index),{})
    def follow(obj,name,index=0):
        link=get(obj,name,index).get("ID")
        if not isinstance(link,str) or link not in objects:raise ValueError("Unresolved native MAT "+name+" link")
        return link
    def number(x):
        return type(x) in (float,int) and isfinite(x)
    if "<this>" not in objects:raise ValueError("No native MAT root")
    root="<this>"
    layer_indices=sorted(i for typ,i in objects[root] if typ=="BSMaterial::LayerID")
    if not layer_indices:raise ValueError("No explicitly resolved MAT layer")
    layer=follow(root,"LayerID",layer_indices[0])
    material=follow(layer,"MaterialID")
    tex=follow(material,"TextureSetID")
    row={}
    for i,field in ((0,"diffuse"),(1,"normal"),(2,"opacity_map"),(3,"roughness_map"),(4,"metallic_map")):
        value=(get(tex,"MRTextureFile",i) or get(tex,"TextureFile",i)).get("FileName")
        if isinstance(value,str) and value:
            value=normalize(value)
            if not value.startswith("textures/"):value="textures/"+value
            if not value.endswith(".dds"):value+=".dds"
            row[field]=value
    color=get(material,"Color").get("Value",{})
    if isinstance(color,dict):color=color.get("Data",color)
    if isinstance(color,dict) and all(number(color.get(k)) for k in ("x","y","z")):
        row["tint"]=tuple(max(0.,min(1.,color[k])) for k in ("x","y","z"))
    normal=get(tex,"MaterialParamFloat").get("Value")
    if number(normal):row["normal_strength"]=max(0.,min(4.,normal))
    alpha=get(root,"AlphaSettingsComponent")
    cutoff=alpha.get("AlphaTestThreshold")
    if alpha.get("HasOpacity") is True and number(cutoff):row["cutout"]=max(0.,min(1.,cutoff))
    if not row:raise ValueError("Native MAT has no supported explicit components")
    return row

class NativeMaterials(PreviewMaterials):
    """Explicit sidecar overrides native JSON; missing/unsupported MAT falls back."""
    def __call__(self,name):
        name=key(name)
        if name not in self.rows:
            self.rows[name]=native_row(self.sources.read(name,2*1024*1024))
        return super().__call__(name)
