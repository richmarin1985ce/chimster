"""Classic LAND material sampling. Base/alpha quadrants in world-aligned coordinates."""
import struct
from math import floor,isfinite
from hashlib import sha256
from .record_graph import Identity
from .lod_dds import decode

def landscape(parts,slots):
    quadrants=[{"base":None,"layers":[]} for _ in range(4)]
    active=None
    for tag,raw in parts:
        if tag in (b"BTXT",b"ATXT"):
            active=None
            if len(raw)!=8:raise ValueError("Bad LAND texture header")
            fid,q,_,layer=struct.unpack("<IBBh",raw)
            if q>=4:raise ValueError("Bad LAND quadrant")
            key=slots.decode(fid)
            if key is None:raise ValueError("Null LAND texture")
            identity=(key.origin,key.local)
            if tag==b"BTXT":
                if quadrants[q]["base"] is not None:raise ValueError("Duplicate base texture")
                quadrants[q]["base"]=identity
            else:
                if any(a["layer"]==layer for a in quadrants[q]["layers"]):raise ValueError("Duplicate alpha layer")
                active={"texture":identity,"layer":layer,"weights":{}}
                quadrants[q]["layers"].append(active)
        elif tag==b"VTXT":
            if active is None or len(raw)%8:raise ValueError("Bad LAND opacity data")
            for pos,value in struct.iter_unpack("<H2xf",raw):
                if pos>=289 or pos in active["weights"] or not isfinite(value) or not 0<=value<=1:raise ValueError("Bad LAND opacity")
                active["weights"][pos]=value
            active=None
    for q in quadrants:q["layers"].sort(key=lambda l:l["layer"])
    return quadrants

def alpha(weights,u,v):
    x=min(16,max(0,u));y=min(16,max(0,v));i=min(15,int(x));j=min(15,int(y))
    a=x-i;b=y-j
    return sum(weights.get((j+dy)*17+i+dx,0)*wx*wy for dy,wy in ((0,1-b),(1,b)) for dx,wx in ((0,1-a),(1,a)))

class Baker:
    def __init__(self,browser,assets):
        self.browser=browser;self.assets=assets;self.cache={};self.layers={};self.issues=set();self.hashes={}
    def get(self,path):
        path=path.replace("\\","/")
        if not path.lower().startswith("textures/"):path="textures/"+path
        key=path.casefold()
        if key not in self.cache:
            if len(self.cache)>=64:raise ValueError("Texture cache budget exceeded")
            raw=self.assets.get(path);image=decode(raw)
            if sum(w*h for w,h,_ in self.cache.values())+image[0]*image[1]>16777216:raise ValueError("Decoded texture budget")
            self.cache[key]=image;self.hashes[key]=sha256(raw).hexdigest()
        return self.cache[key]
    def material(self,key):
        if key not in self.layers:
            row=self.browser.active.get(Identity(*key),{})
            tx=self.browser.active.get(Identity(*row["texture_set"]),{}) if row.get("texture_set") else {}
            paths=tx.get("texture_paths",())
            try:
                if row.get("signature")!="LTEX" or tx.get("signature")!="TXST" or not paths or not paths[0]:raise ValueError("Missing LTEX/TXST link")
                diffuse=self.get(paths[0]);normal=self.get(paths[1]) if len(paths)>1 and paths[1] else None
                self.layers[key]=(diffuse,normal)
            except (OSError,ValueError,KeyError) as exc:
                self.issues.add(str(key)+": "+str(exc));self.layers[key]=None
        return self.layers[key]
    def sample(self,quadrants,u,v,gx,gy,fallback):
        # Quadrants: SW, SE, NW, NE; 17x17 vertex opacity grids.
        qx=int(u>=16);qy=int(v>=16);q=quadrants[qy*2+qx]
        def pixel(image):
            w,h,raw=image
            x=floor(gx*w/4)%w;y=floor(-gy*h/4)%h
            return tuple(raw[(y*w+x)*4:(y*w+x)*4+4])
        def color(key):
            m=self.material(key) if key else None
            return (pixel(m[0]),pixel(m[1]) if m[1] else fallback[1]) if m else fallback
        result=color(q["base"])
        for layer in q["layers"]:
            weight=alpha(layer["weights"],u-qx*16,v-qy*16)
            if weight:
                sample=color(layer["texture"])
                result=tuple(tuple(round(a+(b-a)*weight) for a,b in zip(old,new)) for old,new in zip(result,sample))
        return result
