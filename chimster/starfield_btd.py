"""Bounded Starfield BTDB read-only terrain reader.

Starfield's zero-coordinate header layout, not Fallout 76's layout.
Vertical unit conversion is explicit: no unverified factor is assumed.
"""
import struct,zlib
from math import isfinite
from pathlib import Path
from collections import OrderedDict

class BTD:
    def __init__(self,data):
        if len(data)<44 or len(data)>128*1024*1024:raise ValueError("Invalid BTD size")
        self.data=data;self.cache=OrderedDict()
        magic,ver,low,high,rx,ry,x0,y0,x1,y1,nt=struct.unpack_from("<4sI2f2I4iI",data)
        if magic!=b"BTDB" or ver not in (5,6) or any((x0,y0,x1,y1)) or rx%128 or ry%128 or not 128<=rx<=131072 or not 128<=ry<=131072 or not isfinite(low) or not isfinite(high) or low>high or nt>65536:raise ValueError("Unsupported Starfield BTD header")
        self.nx=rx//128;self.ny=ry//128;self.low=low;self.high=high
        self.min_cell=(-(rx//256),-(ry//256))
        n=self.nx*self.ny
        self.texture_sets=44+4*nt+8*n
        self.height4=self.texture_sets+32*n
        pos=self.height4+256*n;self.tables={}
        for l in (3,2,1,0):
            step=1<<l;w=(self.nx+step-1)//step;h=(self.ny+step-1)//step
            self.tables[l]=(pos,w,h);pos+=8*w*h
        if pos>len(data):raise ValueError("Truncated BTD tables")
        self.start=pos;self.textures=struct.unpack_from("<"+"I"*nt,data,44)
    @classmethod
    def load(cls,path):
        p=Path(path)
        if p.stat().st_size>128*1024*1024:raise ValueError("BTD preview budget exceeded")
        return cls(p.read_bytes())
    @classmethod
    def from_sources(cls,sources,name):
        from .compatibility_asset_lookup import normalize
        key=normalize(name)
        if not key.startswith("terrain/") or not key.endswith(".btd"):raise ValueError("Expected terrain/*.btd")
        return cls(sources.read(key,128*1024*1024))
    def block(self,x,y,l):
        pos,w,h=self.tables[l]
        if not 0<=x<w or not 0<=y<h:raise ValueError("BTD block outside extent")
        key=(x,y,l)
        if key not in self.cache:
            off,size=struct.unpack_from("<2I",self.data,pos+8*(y*w+x))
            a=self.start+off
            if not size or size>1024*1024 or a+size>len(self.data):raise ValueError("Invalid BTD block extent")
            z=zlib.decompressobj();raw=z.decompress(self.data[a:a+size],65537)
            if len(raw)!=65536 or not z.eof or z.unconsumed_tail or z.unused_data:raise ValueError("Invalid compressed BTD block")
            self.cache[key]=raw
            while len(self.cache)>16:self.cache.popitem(last=False)
        else:self.cache.move_to_end(key)
        return self.cache[key]
    def sample(self,x,y,l=0,texture=False):
        """Coordinates in samples from southwest, not native cell IDs."""
        if type(x) is not int or type(y) is not int or l not in (0,1,2,3,4) or not 0<=x<self.nx*128 or not 0<=y<self.ny*128:raise ValueError("BTD sample outside extent")
        if l==4:
            p=self.height4+(self.nx*self.ny*128 if texture else 0)+2*((y//16)*(self.nx*8)+x//16)
            return struct.unpack_from("<H",self.data,p)[0]
        step=1<<l;bx=x//(128*step);by=y//(128*step)
        sx=(x//step)%128;sy=(y//step)%128
        return struct.unpack_from("<H",self.block(bx,by,l),(32768 if texture else 0)+2*(sy*128+sx))[0]
    def heightfield(self,cell_x,cell_y,cells=1,res=129,lod=0,meters_per_height_unit=1.):
        from .starfield_planets import Heightfield
        if type(cells) is not int or not 1<=cells<=4 or res not in (33,65,129,257) or not isfinite(meters_per_height_unit) or not 0<meters_per_height_unit<=1000:raise ValueError("Invalid BTD preview parameters")
        x=(cell_x-self.min_cell[0])*128;y=(cell_y-self.min_cell[1])*128
        if x<0 or y<0 or x+cells*128>self.nx*128 or y+cells*128>self.ny*128:raise ValueError("BTD patch outside extent")
        rows=[]
        for j in range(res):
            row=[]
            for i in range(res):
                a=min(self.nx*128-1,x+round(i*cells*128/(res-1)))
                b=min(self.ny*128-1,y+round(j*cells*128/(res-1)))
                z=self.sample(a,b,lod)
                row.append((self.low+(self.high-self.low)*z/65535)*meters_per_height_unit)
            rows.append(row)
        return Heightfield(rows)

    def layers(self,x,y,l=0):
        """Return normalized native layer weights keyed by raw LTEX IDs.

        Five three-bit blend values overlay the default texture in
        quadrant-specific order. Unmapped/absent slots are ignored.
        """
        packed=self.sample(x,y,l,texture=True)
        q=(y//64)*(self.nx*2)+x//64
        entries=self.data[self.texture_sets+q*8:self.texture_sets+(q+1)*8]
        slots=[self.textures[len(self.textures)-i] if 0<i<=len(self.textures) else None for i in entries]
        base=next((i for i in reversed(slots) if i is not None),None)
        weights={base:1.}
        # Stored alphas are in the reverse of compositing order.
        for n,key in enumerate(reversed(slots[:5])):
            a=((packed>>(3*(4-n)))&7)/7
            if key is None or not a:continue
            weights={k:w*(1-a) for k,w in weights.items() if w*(1-a)>0}
            weights[key]=weights.get(key,0.)+a
        return weights

def diagnostic_color(key):
    from hashlib import sha256
    if key is None:return (.35,.35,.35)
    digest=sha256(struct.pack("<I",key)).digest()
    return tuple(.18+.68*v/255 for v in digest[:3])

def layer_image(btd,cell_x,cell_y,u0,v0,u1,v1,cells=1,size=64,colors=None):
    """Bake native blend weights into a diagnostic preview, not game textures."""
    from .gpu_viewport import ImageMap
    if size not in (16,32,64,128) or not 1<=cells<=4 or not 0<=u0<u1<=1 or not 0<=v0<v1<=1:raise ValueError("Invalid terrain texture preview extent")
    x0=(cell_x-btd.min_cell[0])*128;y0=(cell_y-btd.min_cell[1])*128
    if x0<0 or y0<0 or x0+128*cells>btd.nx*128 or y0+128*cells>btd.ny*128:raise ValueError("Texture patch outside BTD")
    colors=colors or {};rgba=bytearray()
    for y in range(size):
        for x in range(size):
            # Rows of an ImageMap are top-to-bottom; terrain UVs increase north.
            u=u0+(u1-u0)*x/(size-1);v=v1-(v1-v0)*y/(size-1)
            a=min(btd.nx*128-1,x0+round(u*cells*128));b=min(btd.ny*128-1,y0+round(v*cells*128))
            weights=btd.layers(a,b)
            rgb=[0.,0.,0.]
            for k,w in weights.items():
                col=colors.get(k,diagnostic_color(k))
                if len(col)!=3 or any(not isfinite(z) or not 0<=z<=1 for z in col):raise ValueError("Invalid LTEX preview color")
                for i in range(3):rgb[i]+=w*col[i]
            rgba.extend(max(0,min(255,round(c*255))) for c in rgb);rgba.append(255)
    return ImageMap(size,size,bytes(rgba)).validate()

def apply_layer_preview(scene,report,btd,cell_x,cell_y,cells=1,colors=None):
    """Attach per-tile native-weight diagnostic diffuse maps to every LOD."""
    from .gpu_viewport import Material
    mats={}
    for ty in range(3):
        for tx in range(3):
            name=f"planet-tile-{tx}-{ty}"
            mat="btd-layer-"+name
            image=layer_image(btd,cell_x,cell_y,tx/3,ty/3,(tx+1)/3,(ty+1)/3,cells,colors=colors)
            mats[mat]=Material(diffuse=image).validate()
            for suffix in ("","@lod1","@lod2"):
                mesh=scene.assets[name+suffix]
                mesh.faces=[(tri,mat) for tri,_ in mesh.faces]
    report["preview_materials"]=mats
    report["texture_source"]="native BTD blend weights, diagnostic LTEX colors"
    report["issues"]=["Native height samples and texture weights; vertical scale and geographic alignment supplied by user; diagnostic colors, not native material textures"]
    return scene,report

class BTDStream:
    """Bounded moving 3x3 native cell window with shared edge samples."""
    def __init__(self,btd,catalog,k,cell_x,cell_y,lat,lon,cell_km,scale=1.,resolution=32):
        if not all(isfinite(n) for n in (cell_km,scale,lat,lon)) or not .001<=cell_km<=100 or not 0<scale<=1000 or resolution not in (16,32,64):raise ValueError("Invalid BTD streaming parameters")
        if not btd.min_cell[0]<=cell_x<btd.min_cell[0]+btd.nx or not btd.min_cell[1]<=cell_y<btd.min_cell[1]+btd.ny:raise ValueError("Initial BTD cell outside extent")
        self.btd=btd;self.catalog=catalog;self.k=k;self.start=(cell_x,cell_y);self.lat=lat;self.lon=lon
        self.cell_km=cell_km;self.scale=scale;self.res=resolution;self.center=None;self.cache=OrderedDict()
    def tile(self,x,y):
        from .starfield_planets import grid,skirt
        from .gpu_viewport import Material
        key=(x,y)
        if key in self.cache:
            self.cache.move_to_end(key);return self.cache[key]
        b=self.btd;factor=self.scale/(self.cell_km*1000/32)
        sx=(x-b.min_cell[0])*128;sy=(y-b.min_cell[1])*128
        name=f"btd-{x}-{y}"
        def point(u,v):
            a=min(b.nx*128-1,sx+round(u*128));c=min(b.ny*128-1,sy+round(v*128))
            height=b.low+(b.high-b.low)*b.sample(a,c)/65535
            return ((u-.5)*32,(v-.5)*32,height*factor)
        meshes=[skirt(grid(r,point,lambda u,v:name),r,max(1.,abs(b.high-b.low)*factor*.25)) for r in (self.res,self.res//2,self.res//4)]
        material=Material(diffuse=layer_image(b,x,y,0,0,1,1,size=32))
        self.cache[key]=(name,meshes,material)
        while len(self.cache)>18:self.cache.popitem(last=False)
        return self.cache[key]
    def update(self,x=0.,y=0.):
        from math import floor,asin,atan2,degrees
        from .scene import Scene,Instance
        from .starfield_planets import report,direction_at
        if not all(isfinite(v) for v in (x,y)):raise ValueError("Invalid BTD view coordinates")
        center=(self.start[0]+floor(x/32+.5),self.start[1]+floor(y/32+.5))
        if center==self.center:return None
        b=self.btd
        if not b.min_cell[0]<=center[0]<b.min_cell[0]+b.nx or not b.min_cell[1]<=center[1]<b.min_cell[1]+b.ny:raise ValueError("End of native BTD coverage")
        assets={};materials={};instances=[]
        for cy in range(max(b.min_cell[1],center[1]-1),min(b.min_cell[1]+b.ny,center[1]+2)):
            for cx in range(max(b.min_cell[0],center[0]-1),min(b.min_cell[0]+b.nx,center[0]+2)):
                name,meshes,mat=self.tile(cx,cy)
                for i,m in enumerate(meshes):assets[name+("@lod"+str(i) if i else "")]=m
                materials[name]=mat;instances.append(Instance(name,name,(cx-center[0])*32,(cy-center[1])*32))
        p=self.catalog.planets[self.k]
        radius=p.get("radius_km",0)
        dx=center[0]-self.start[0];dy=center[1]-self.start[1]
        lat,lon=self.lat,self.lon
        if radius>0:
            q=direction_at(lat,lon,dx*self.cell_km,dy*self.cell_km,radius)
            lat=degrees(asin(max(-1.,min(1.,q[2]))));lon=degrees(atan2(q[1],q[0]))
        info=report(self.k,materials,{},len(instances),"native BTD landing")
        info.update(planet_stream=True,latitude=lat,longitude=lon,origin_game_units=(dx*32,dy*32,0),height_source="native BTD samples (user scale)",texture_source="native BTD weights, diagnostic colors")
        info["render_preview"]["planet_solar"]={"latitude":lat,"atmosphere":p.get("atmosphere")}
        info["issues"]=["Native BTD coverage only; geographic alignment, cell width and vertical conversion are user supplied; diagnostic LTEX colors"]
        self.center=center
        return Scene(assets,instances),info
