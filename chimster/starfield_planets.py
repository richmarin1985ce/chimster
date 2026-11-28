"""Native Starfield planet metadata and independent bounded planetary previews.

The native surface generation algorithm and raw surface-tree ID remapping
are not implemented. Preview heights and biome geography are illustrative.
"""
from math import sin,cos,pi,radians,degrees,isfinite,sqrt,floor,asin,atan2
from collections import OrderedDict,Counter
import struct
from hashlib import sha256
from .starfield_preview import Plugin,one,string,link,floats,rgb,label
from .flora import Mesh
from .scene import Scene,Instance
from .gpu_viewport import Material
from .lod import validate_mesh

def decode_planet(fields,slots):
    body=False;out={"name":string(one(fields,b"EDID")),"worldspaces":[],"biomes":[]}
    for tag,raw in fields:
        if tag==b"BDST":body=True;continue
        if tag==b"BDED":body=False;continue
        if tag==b"ANAM" and body:out["name"]=string(raw) or out["name"]
        if tag==b"CNAM" and body and len(raw)==1:out["kind"]=raw[0]
        if tag==b"FNAM" and not body and len(raw)==4:out["tree"]=slots.decode(struct.unpack("<I",raw)[0])
        if tag==b"FNAM" and body and len(raw)==24:
            vals=struct.unpack("<d3fi",raw)
            if all(isfinite(v) for v in vals[:4]):
                out.update(mass_kg=vals[1],radius_km=vals[2],gravity=vals[3])
        if tag==b"GNAM" and body and len(raw)==12:out["system_ids"]=struct.unpack("<3I",raw)
        if tag==b"INAM" and body and len(raw)==16:
            aid,density,ray,mie=struct.unpack("<I3f",raw)
            if all(isfinite(x) and x>=0 for x in (density,ray,mie)):out["atmosphere"]=(aid,density,ray,mie)
        if tag==b"KNAM" and body and len(raw)>=29:
            size,=struct.unpack_from("<I",raw)
            if size<=4096 and len(raw)==4+size+25:
                freq,hfreq,kind,seed,height=struct.unpack_from("<2dBif",raw,4+size)
                if all(isfinite(v) for v in (freq,hfreq,height)) and height>=0:
                    out.update(noise_file=string(raw[4:4+size]),biome_frequency=freq,height_frequency=hfreq,terrain_seed=seed,max_height_m=height)
        if tag==b"CNAM" and not body and len(raw)%20==0:
            for a,b,fid in struct.iter_unpack("<ddI",raw):
                if isfinite(a) and isfinite(b):
                    # xEdit labels the first field latitude; Mutagen labels it
                    # longitude. Keep the raw values as well as the chosen display order.
                    out["worldspaces"].append((slots.decode(fid),a,b))
        if tag==b"PPBD" and len(raw)>=16:
            fid,chance=struct.unpack_from("<If",raw)
            if isfinite(chance) and chance>=0:out["biomes"].append((slots.decode(fid),chance))
        if tag==b"RSCS" and len(raw)==4:out["seed"]=struct.unpack("<i",raw)[0]
        if tag in (b"TEMP",b"DENS") and len(raw)==4:
            val=struct.unpack("<f",raw)[0]
            if isfinite(val):out["temperature" if tag==b"TEMP" else "density"]=val
    return out

def decode_biome(fields,slots):
    out={"name":string(one(fields,b"EDID")),"climate":link(fields,b"ENAM",slots),"water":link(fields,b"INAM",slots),"style":link(fields,b"NNAM",slots)}
    wet=one(fields,b"MNAM",1);out["wet"]=bool(wet and wet[0])
    for tag,name in ((b"CNAM","color"),(b"BMC1","surface"),(b"BMC2","surface2"),(b"BMC3","rock")):
        raw=one(fields,tag,4)
        if raw is not None:out[name]=rgb(raw)
    return out

class Planets:
    def __init__(self,paths):
        self.plugins=[];loaded=set();self.planets={};self.biomes={};self.worlds={};self.stars={}
        for path in paths:
            p=Plugin(path);name=p.slots.names[-1]
            if name in loaded or any(m not in loaded for m in p.slots.names[:-1]):raise ValueError("Select masters before dependents")
            loaded.add(name);self.plugins.append(p)
            for k,sig,flags,w,c,fields,owner in p.scan(lambda sig,*_:sig in (b"PNDT",b"BIOM",b"WRLD",b"STDT")):
                target={b"PNDT":self.planets,b"BIOM":self.biomes,b"WRLD":self.worlds,b"STDT":self.stars}[sig]
                if flags&0x20:target.pop(k,None);continue
                if sig==b"PNDT":row=decode_planet(fields,p.slots)
                elif sig==b"BIOM":row=decode_biome(fields,p.slots)
                elif sig==b"WRLD":row={"name":string(one(fields,b"EDID")),"biome":link(fields,b"BNAM",p.slots),"climate":link(fields,b"CNAM",p.slots)}
                else:
                    raw=one(fields,b"DNAM",4);row={"name":string(one(fields,b"ANAM")),"system_id":struct.unpack("<I",raw)[0] if raw else None}
                target[k]=row
                if len(target)>100000:raise ValueError("Planet index budget")
        if not self.plugins:raise ValueError("Select Starfield plugins")
    def choices(self,query=""):
        q=query.casefold()
        return sorted(((k,v) for k,v in self.planets.items() if q in (label(k)+" "+v["name"]).casefold()),key=lambda x:(x[1]["name"],label(x[0])))[:500]
    def sites(self,k,order="xedit"):
        if order not in ("xedit","mutagen"):raise ValueError("Unknown coordinate convention")
        rows=[]
        for world,a,b in self.planets[k]["worldspaces"]:
            lat,lon=(a,b) if order=="xedit" else (b,a)
            lat=degrees(lat);lon=degrees(lon)
            if not -90<=lat<=90:continue
            rows.append((world,lat,(lon+180)%360-180,self.worlds.get(world,{}).get("name","")))
        return rows
    def surface_record(self,k):
        """Inspect native tree or pattern arrays lazily; IDs are raw on disk."""
        result=None
        for p in self.plugins:
            for rid,sig,flags,w,c,fields,owner in p.scan(lambda sig,fid,c,slots:sig in (b"SFTR",b"SFPT",b"SFBK") and slots.decode(fid)==k):
                if flags&0x20:result=None;continue
                arrays=[]
                for tag,raw in fields:
                    if sig==b"SFTR" and tag in (b"FNAM",b"ENAM") and len(raw)==65536*4 or sig==b"SFPT" and tag in (b"BNAM",b"FNAM",b"EFRM") and len(raw)==256*4:
                        arrays.append((tag.decode(),raw))
                result={"signature":sig.decode(),"name":string(one(fields,b"EDID")),"arrays":arrays,"filter":string(one(fields,b"NAM1")),"water_height":floats(one(fields,b"WHGT",4),1)}
        return result

def unit(lat,lon):
    a,b=radians(lat),radians(lon)
    return (cos(a)*cos(b),cos(a)*sin(b),sin(a))
def basis(lat,lon):
    a,b=radians(lat),radians(lon)
    return unit(lat,lon),(-sin(b),cos(b),0),(-sin(a)*cos(b),-sin(a)*sin(b),cos(a))
def direction_at(lat,lon,x,y,radius):
    up,e,n=basis(lat,lon);d=sqrt(x*x+y*y)
    if not d:return up
    angle=d/radius
    return tuple(up[i]*cos(angle)+(x*e[i]+y*n[i])/d*sin(angle) for i in range(3))
def hash_seed(k,planet):
    return int.from_bytes(sha256(label(k).encode()).digest()[:4],"little")^planet.get("terrain_seed",planet.get("seed",0))
def relief(p,seed):
    a,b,c=p
    phase=(seed&65535)/65535*2*pi
    return .52*sin(13*a+7*b+phase)*cos(11*c-4*a)+.27*sin(37*b-19*c+phase)+.13*cos(91*a+63*c-phase)+.08*sin(191*b+113*c+phase)
def palette(catalog,k):
    out={}
    for i,(biome,chance) in enumerate(catalog.planets[k]["biomes"]):
        row=catalog.biomes.get(biome,{})
        if chance>0:out["planet-biome-"+str(i)]=(chance,row.get("surface",row.get("color",(.45,.42,.38))))
    return out or {"planet-biome-0":(1.,(.45,.42,.38))}
def material_at(p,seed,colors):
    value=(relief(p,seed+101)+1)*.5*sum(w for w,c in colors.values())
    for name,(w,c) in colors.items():
        value-=w
        if value<=0:return name
    return next(reversed(colors))
def grid(res,point,mat):
    mesh=Mesh()
    for y in range(res+1):
        for x in range(res+1):
            mesh.vertices.append(point(x/res,y/res));mesh.uv.append((x/res,y/res))
    for y in range(res):
        for x in range(res):
            a=y*(res+1)+x;b=a+1;c=a+res+1;d=c+1
            name=mat((x+.5)/res,(y+.5)/res)
            mesh.faces.extend([((a,b,d),name),((a,d,c),name)])
    validate_mesh(mesh);return mesh
def report(k,materials,fx,tiles,mode):
    return dict(cell=label(k),cells=1,land_tiles=tiles,proxy_references=0,model_references=0,skipped_references=0,origin_game_units=(0,0,0),environment={},starfield=True,preview_materials=materials,render_preview=dict(effects=fx,lights=[],water_level=None),planet_mode=mode,issues=["Illustrative procedural preview, not Starfield's native surface"])
def globe(catalog,k,res=16):
    if res not in (8,16,32):raise ValueError("Invalid globe resolution")
    p=catalog.planets[k];seed=hash_seed(k,p);colors=palette(catalog,k)
    assets={};instances=[]
    # Six cube faces avoid singular poles and duplicate seam geometry.
    faces=((0,1,2,1),(0,2,1,-1),(1,2,0,1),(1,0,2,-1),(2,0,1,1),(2,1,0,-1))
    for i,(axis,u,v,sign) in enumerate(faces):
        def vector(x,y):
            q=[0.,0.,0.];q[axis]=sign;q[u]=2*x-1;q[v]=2*y-1
            length=sqrt(sum(z*z for z in q));return tuple(z/length for z in q)
        def point(x,y):
            q=vector(x,y);radius=40*(1+.012*relief(q,seed))
            return tuple(z*radius for z in q)
        name="planet-face-"+str(i)
        mesh=grid(res,point,lambda x,y:material_at(vector(x,y),seed,colors))
        assets[name]=mesh;instances.append(Instance(name,name))
    mats={name:Material(tint=col) for name,(w,col) in colors.items()}
    return Scene(assets,instances),report(k,mats,{},6,"globe")
class Heightfield:
    """Explicit user-supplied square height samples in meters."""
    def __init__(self,rows):
        n=len(rows)
        if n<2 or n>513 or any(len(row)!=n for row in rows):raise ValueError("Expected square heightfield of 2–513 samples")
        if any(type(h) not in (int,float) or not isfinite(h) or abs(h)>100000 for row in rows for h in row):raise ValueError("Invalid height sample")
        self.rows=tuple(tuple(row) for row in rows);self.n=n
    @classmethod
    def load(cls,path):
        import json
        from pathlib import Path
        p=Path(path)
        if p.stat().st_size>8*1024*1024:raise ValueError("Heightfield file exceeds budget")
        data=json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data,dict) or data.get("version")!=1 or data.get("units")!="meters" or not isinstance(data.get("heights"),list):raise ValueError("Expected heightfield JSON version 1 in meters")
        return cls(data["heights"])
    def sample(self,u,v):
        x=max(0.,min(1.,u))*(self.n-1);y=max(0.,min(1.,v))*(self.n-1)
        a=min(self.n-2,int(x));b=min(self.n-2,int(y));fx=x-a;fy=y-b
        return (1-fy)*((1-fx)*self.rows[b][a]+fx*self.rows[b][a+1])+fy*((1-fx)*self.rows[b+1][a]+fx*self.rows[b+1][a+1])

def skirt(mesh,res,depth):
    """Hide mixed-LOD edge gaps with downward-facing perimeter strips."""
    edge=list(range(res+1))+[y*(res+1)+res for y in range(1,res+1)]+[res*(res+1)+x for x in range(res-1,-1,-1)]+[y*(res+1) for y in range(res-1,0,-1)]
    start=len(mesh.vertices)
    for i in edge:
        x,y,z=mesh.vertices[i];mesh.vertices.append((x,y,z-depth));mesh.uv.append(mesh.uv[i])
    mat=mesh.faces[0][1]
    for i,a in enumerate(edge):
        j=(i+1)%len(edge);b=edge[j];c=start+i;d=start+j
        mesh.faces.extend([((a,c,d),mat),((a,d,b),mat)])
    return mesh

def terrain(catalog,k,lat,lon,span_km=8.,resolution=32,heightfield=None,center=(0,0),cache=None):
    if not all(isfinite(x) for x in (lat,lon,span_km)) or not -90<=lat<=90 or not -180<=lon<=180 or not .1<=span_km<=100 or resolution not in (16,32,64):raise ValueError("Invalid landing preview")
    p=catalog.planets[k];radius=p.get("radius_km",0)
    if not 1<=radius<=1000000 or span_km>radius*.1:raise ValueError("Missing radius or oversized local patch")
    if len(center)!=2 or any(type(i) is not int or abs(i)>100000 for i in center):raise ValueError("Invalid streaming tile center")
    if heightfield is not None and center!=(0,0):raise ValueError("Imported heightfield is limited to its original extent")
    seed=hash_seed(k,p);colors=palette(catalog,k)
    # Scale to a 96-unit working area; use spherical geodesic coordinates
    # for sample continuity, and a shared local tangent-plane render origin.
    meters_per_unit=span_km*1000/96
    height=min(20000.,p.get("max_height_m",500.))
    assets={};instances=[]
    for ty in range(3):
        for tx in range(3):
            gx,gy=tx+center[0],ty+center[1]
            name=f"planet-tile-{gx}-{gy}"
            def coord(x,y):return ((gx+x-1.5)*span_km/3,(gy+y-1.5)*span_km/3)
            cx=(tx-1)*32;cy=(ty-1)*32
            def point(x,y):
                a,b=coord(x,y);q=direction_at(lat,lon,a,b,radius)
                if heightfield is not None:z=heightfield.sample((tx+x)/3,(ty+y)/3)/meters_per_unit
                else:
                    # Global relief plus higher-frequency local-scale detail.
                    detail=.5*sin(q[0]*radius*1.7+q[1]*radius*.9+seed%31)*cos(q[2]*radius*2.1)+.25*sin(q[1]*radius*6.2-q[2]*radius*3.4+seed%47)
                    z=height*(.65*relief(q,seed)+.35*detail)/meters_per_unit
                return ((x-.5)*32,(y-.5)*32,z)
            def mat(x,y):return material_at(direction_at(lat,lon,*coord(x,y),radius),seed,colors)
            for tier,r in enumerate((resolution,resolution//2,resolution//4)):
                asset=name+("@lod"+str(tier) if tier else "")
                if cache is not None and asset in cache:
                    mesh=cache[asset];cache.move_to_end(asset)
                else:
                    mesh=skirt(grid(r,point,mat),r,max(1.,height/meters_per_unit*.25))
                    if cache is not None:cache[asset]=mesh
                assets[asset]=mesh
            instances.append(Instance(name,name,cx,cy))
    mats={name:Material(tint=col) for name,(w,col) in colors.items()}
    fx={}
    if "atmosphere" in p:
        _,density,ray,mie=p["atmosphere"]
        fx=dict(fog_density=min(.12,density*.012),scatter_strength=min(2.,(ray+mie)*.5),fog_falloff=.02,volume_distance=160.)
    r=report(k,mats,fx,9,"landing")
    r.update(latitude=lat,longitude=lon,span_km=span_km,meters_per_unit=meters_per_unit,stream_center=center,origin_game_units=(center[0]*32,center[1]*32,0),height_source="imported meters" if heightfield is not None else "illustrative procedural")
    if heightfield is not None:r["issues"]=["User-supplied heightfield; native biome placement remains illustrative"]
    return Scene(assets,instances),r

class LandingStream:
    """Recenter a bounded 3x3 tile window in a fixed geographic tangent chart."""
    def __init__(self,catalog,k,lat,lon,span_km=8.,resolution=32):
        self.catalog=catalog;self.k=k;self.lat=lat;self.lon=lon;self.span=span_km;self.resolution=resolution
        self.center=None;self.cache=OrderedDict()
    def update(self,x=0.,y=0.):
        if not all(isfinite(v) for v in (x,y)):raise ValueError("Invalid streaming coordinates")
        center=(floor(x/32+.5),floor(y/32+.5))
        if center==self.center:return None
        radius=self.catalog.planets[self.k]["radius_km"]
        if sqrt(sum(v*v for v in center))*self.span/3+self.span>radius*.1:raise ValueError("Outside landing chart; select a new geographic location")
        scene,info=terrain(self.catalog,self.k,self.lat,self.lon,self.span,self.resolution,center=center,cache=self.cache)
        while len(self.cache)>54:self.cache.popitem(last=False)
        self.center=center
        q=direction_at(self.lat,self.lon,center[0]*self.span/3,center[1]*self.span/3,radius)
        info["latitude"]=degrees(asin(max(-1.,min(1.,q[2]))));info["longitude"]=degrees(atan2(q[1],q[0]))
        info["planet_stream"]=True
        return scene,info

def surface_summary(row):
    """Summarize documented native arrays without guessing runtime-ID remapping."""
    if row is None:return []
    results=[]
    for tag,raw in row["arrays"]:
        size=256 if row["signature"]=="SFPT" else 65536
        counts=Counter(v[0] for v in struct.iter_unpack("<I",raw) if v[0])
        results.append(dict(tag=tag,side=16 if size==256 else 256,nonzero=sum(counts.values()),unique=len(counts),top=[(f"{v:08X}",n) for v,n in counts.most_common(12)]))
    return results
