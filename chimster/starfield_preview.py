"""Experimental Starfield full-master cell preview, streaming and read-only.

No runtime-ID translation, native writes, planet terrain or .mesh decoding.
Layouts independently described by Mutagen SF1 and xEdit SF1 schemas.
"""
from pathlib import Path
from dataclasses import asdict
from math import isfinite, sin, cos, radians, degrees
import struct,zlib
from .record_graph import Slots,Identity
from .loadorder import plugin_name
from .scene import Scene,Instance
from .architecture import box_mesh
from .render_effects import LocalLight

MAX_PAYLOAD=16*1024*1024
MAX_CELLS=100000
MAX_REFS=5000

def stamp(p):
    s=p.stat()
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def parts(payload,flags=0):
    if flags&0x40000:
        if len(payload)<4:raise ValueError("Truncated compressed record")
        n=struct.unpack_from("<I",payload)[0]
        if n>MAX_PAYLOAD:raise ValueError("Starfield record exceeds budget")
        dec=zlib.decompressobj();payload=dec.decompress(payload[4:],n+1)
        if len(payload)!=n or not dec.eof or dec.unused_data or dec.unconsumed_tail:raise ValueError("Bad compressed record")
    out=[];i=0;extended=None
    while i<len(payload):
        if i+6>len(payload):raise ValueError("Truncated Starfield subrecord")
        tag,size=struct.unpack_from("<4sH",payload,i);i+=6
        if tag==b"XXXX":
            if extended is not None or size!=4 or i+4>len(payload):raise ValueError("Invalid XXXX")
            extended=struct.unpack_from("<I",payload,i)[0];i+=4;continue
        if extended is not None:size,extended=extended,None
        if i+size>len(payload):raise ValueError("Invalid Starfield subrecord extent")
        out.append((tag,payload[i:i+size]));i+=size
    if extended is not None:raise ValueError("Dangling XXXX")
    return out

def one(items,tag,size=None):
    hits=[v for t,v in items if t==tag]
    return hits[0] if len(hits)==1 and (size is None or len(hits[0])==size) else None

def string(raw):
    return raw[:-1].decode("cp1252",errors="replace") if raw and raw.endswith(b"\0") and b"\0" not in raw[:-1] else ""

def link(items,tag,slots):
    raw=one(items,tag,4)
    return slots.decode(struct.unpack("<I",raw)[0]) if raw is not None else None

def floats(raw,n,offset=0):
    if raw is None or len(raw)<offset+4*n:return None
    result=struct.unpack_from("<"+"f"*n,raw,offset)
    return result if all(isfinite(v) for v in result) else None

def rgb(raw,offset=0):
    return tuple(v/255 for v in raw[offset:offset+3])

def light(items):
    raw=one(items,b"DAT2",76)
    if raw is None:return None
    radius=struct.unpack_from("<f",raw,4)[0]
    flags=struct.unpack_from("<I",raw,12)[0]
    fov=struct.unpack_from("<f",raw,20)[0]
    kelvin,lumen=struct.unpack_from("<II",raw,48)
    kind=raw[56]
    if not isfinite(radius) or radius<=0 or not isfinite(fov) or kind not in (0,1,2):return None
    return dict(radius=radius,flags=flags,color=rgb(raw,8),fov=fov,kind=kind,kelvin=kelvin,lumen=lumen)

def cell_lighting(raw,units):
    if raw is None or len(raw)!=108:return {}
    return lighting_prefix(raw,units)

def lighting_prefix(raw,units):
    nf=floats(raw,2,12);fade=floats(raw,1,28)
    out=dict(ambient=sum(rgb(raw))/3,sun_color=rgb(raw,4),fog_color=rgb(raw,8))
    if nf and nf[1]>max(0,nf[0]):out["fog_density"]=min(1.,2.3*units/(nf[1]-nf[0]))
    if fade:out["sun_intensity"]=max(0.,min(4.,fade[0]))
    return out

def water(items,units):
    # xEdit SF1 DNAM exact documented prefix and two known tails.
    raw=one(items,b"DNAM")
    if raw is None or len(raw) not in (152,164,165):return {}
    out=dict(water_color=rgb(raw,4),water_deep_color=rgb(raw,8))
    alpha=floats(raw,2,20);reflect=floats(raw,1,64);fog=floats(raw,3,40)
    if alpha:out["water_opacity"]=max(0.,min(1.,sum(alpha)/2))
    if reflect:out["water_reflectivity"]=max(0.,min(1.,reflect[0]))
    if fog and fog[2]>max(0.,fog[1]):out["underwater_density"]=max(0.,min(1.,2.3*max(0.,fog[0])*units/(fog[2]-fog[1])))
    return out

class Plugin:
    def __init__(self,path):
        self.path=Path(path).resolve(strict=True);self.initial=stamp(self.path)
        if self.path.suffix.casefold() not in (".esm",".esp",".esl"):raise ValueError("Expected Starfield plugin")
        with self.path.open("rb") as f:
            header=f.read(24)
            if len(header)!=24 or header[:4]!=b"TES4":raise ValueError("Expected 24-byte Starfield TES4 header")
            size,flags=struct.unpack_from("<II",header,4)
            if flags&0x700 or self.path.suffix.casefold()==".esl":raise ValueError("Starfield small, medium and overlay masters are not yet supported")
            if size>MAX_PAYLOAD or size+24>self.initial[2]:raise ValueError("Invalid TES4 extent")
            fields=parts(f.read(size),flags)
            hedr=one(fields,b"HEDR",12)
            if hedr is None:raise ValueError("Missing Starfield HEDR")
            version=struct.unpack_from("<f",hedr)[0]
            # The caller selects Starfield explicitly; reject older TES4-family headers.
            form_version=struct.unpack_from("<H",header,20)[0]
            if not isfinite(version) or not .9<=version<=2.0 or form_version<500:raise ValueError("Not a supported Starfield header")
            masters=[string(v) for tag,v in fields if tag==b"MAST"]
            if any(not v for v in masters):raise ValueError("Invalid master name")
            self.slots=Slots(self.path.name,masters);self.start=24+size;self.localized=bool(flags&0x80)
        self.check()
    def check(self):
        if stamp(self.path)!=self.initial:raise ValueError("Starfield plugin changed; reload")
    def scan(self,accept):
        """Visit headers without loading unrelated records or whole ESMs."""
        self.check()
        with self.path.open("rb") as f:
            def walk(begin,end,world=None,cell=None,depth=0):
                if depth>64:raise ValueError("Group nesting limit")
                pos=begin
                while pos<end:
                    f.seek(pos);header=f.read(24)
                    if len(header)!=24 or pos+24>end:raise ValueError("Truncated Starfield record header")
                    sig,size,flags,fid=struct.unpack_from("<4sIII",header)
                    if sig==b"GRUP":
                        stop=pos+size
                        if stop<pos+24 or stop>end:raise ValueError("Invalid group extent")
                        kind=fid;owner=self.slots.decode(flags) if kind in (1,6,8,9) else None
                        yield from walk(pos+24,stop,owner if kind==1 else world,None if kind==1 else owner if kind in (6,8,9) else cell,depth+1)
                    else:
                        stop=pos+24+size
                        if stop>end:raise ValueError("Invalid record extent")
                        # Resolve identities only for signatures relevant to the scan.
                        if accept(sig,fid,cell,self.slots):
                            key=self.slots.decode(fid)
                            if key is None:raise ValueError("Null Starfield record ID")
                            if flags&0x20:fields=[]
                            else:
                                if size>MAX_PAYLOAD:raise ValueError("Selected record exceeds budget")
                                fields=parts(f.read(size),flags)
                            yield key,sig,flags,world,cell,fields,self
                    pos=stop
            yield from walk(self.start,self.initial[2])
        self.check()

def label(key):
    return f"{key.origin}:{key.local:06X}"

class Catalog:
    def __init__(self,paths):
        self.plugins=[];loaded=set()
        for path in paths:
            plugin=Plugin(path)
            name=plugin.slots.names[-1]
            if name in loaded or any(m not in loaded for m in plugin.slots.names[:-1]):raise ValueError("Select all full masters before dependents in load order")
            self.plugins.append(plugin);loaded.add(name)
        if not self.plugins:raise ValueError("Select Starfield plugins")
        self.cells={}
        for p in self.plugins:
            for key,sig,flags,world,cell,fields,owner in p.scan(lambda sig,*_:sig==b"CELL"):
                if flags&0x20:self.cells.pop(key,None);continue
                keep={b"EDID",b"FULL",b"DATA",b"XCLL",b"XCLW",b"XCWT",b"LTMP"}
                self.cells[key]=(world,[(tag,raw) for tag,raw in fields if tag in keep and len(raw)<=4096],owner)
                if len(self.cells)>MAX_CELLS:raise ValueError("Cell index budget exceeded")
    def choices(self,query="",limit=100):
        q=query.casefold()
        out=[]
        for key,(world,fields,p) in self.cells.items():
            name=string(one(fields,b"EDID")) or (string(one(fields,b"FULL")) if not p.localized else "")
            if q in (label(key)+" "+name).casefold():out.append((key,name))
        return sorted(out,key=lambda x:(x[1].casefold(),x[0]))[:limit]
    def preview(self,key,units=1.,meshes=None):
        if not isfinite(units) or not .001<=units<=10000:raise ValueError("Invalid game units per preview unit")
        world,fields,owner=self.cells[key]
        # Track moved/deleted overrides by resolving reference IDs in every cell,
        # but read payload only for target-cell references or known overrides.
        refs={}
        for p in self.plugins:
            def wants(sig,fid,cell,slots):
                return sig==b"REFR" and (cell==key or slots.decode(fid) in refs)
            for rid,sig,flags,w,cell,items,plugin in p.scan(wants):
                if flags&0x20 or cell!=key:refs.pop(rid,None);continue
                refs[rid]=(flags,items,plugin)
                if len(refs)>MAX_REFS:raise ValueError("Selected cell reference budget exceeded")
        basekeys={link(items,b"NAME",p.slots) for flags,items,p in refs.values()}
        waterkey=link(fields,b"XCWT",owner.slots);template=link(fields,b"LTMP",owner.slots)
        wanted=basekeys|{waterkey,template,world};wanted.discard(None)
        records={}
        for p in self.plugins:
            def wants_base(sig,fid,cell,slots):
                return sig not in (b"REFR",b"CELL",b"LAND",b"NAVM") and slots.decode(fid) in wanted
            for rid,sig,flags,w,cell,items,plugin in p.scan(wants_base):
                if flags&0x20:records.pop(rid,None)
                else:records[rid]=(sig,items,plugin)
        # Resolve direct world water/height, but do not guess parent flags or planet cell size.
        worldrow=records.get(world)
        height=floats(one(fields,b"XCLW",4),1)
        if worldrow and worldrow[0]==b"WRLD":
            if waterkey is None:
                waterkey=link(worldrow[1],b"NAM2",worldrow[2].slots)
                if waterkey is not None and waterkey not in records:
                    for p in self.plugins:
                        for rid,sig,flags,w,cell,items,plugin in p.scan(lambda sig,fid,c,s: sig==b"WATR" and s.decode(fid)==waterkey):
                            if flags&0x20:records.pop(rid,None)
                            else:records[rid]=(sig,items,plugin)
            if height is None:
                v=floats(one(worldrow[1],b"DNAM",8),2)
                if v:height=(v[1],)
        fx=cell_lighting(one(fields,b"XCLL"),units)
        if not fx and template in records and records[template][0]==b"LGTM":
            raw=one(records[template][1],b"DATA",108)
            if raw:fx=lighting_prefix(raw,units)
        flags=one(fields,b"DATA",4)
        wet=bool(flags and struct.unpack("<I",flags)[0]&2)
        level=height[0]/units if wet and height and abs(height[0]/units)<1e7 else None
        if level is not None and waterkey in records and records[waterkey][0]==b"WATR":fx.update(water(records[waterkey][1],units))
        assets={"proxy":box_mesh((-.18,-.18,0),(.18,.18,.65),"proxy")}
        placed=[];lights=[];models=set();skipped=0;light_count=0;model_count=0;issues=[];failed=set()
        for rid,(flags,items,p) in sorted(refs.items()):
            transform=floats(one(items,b"DATA",24),6)
            scale=floats(one(items,b"XSCL",4),1)
            scale=scale[0] if scale else 1.
            if not transform or scale<=0 or flags&0x800:skipped+=1;continue
            xyz=tuple(v/units for v in transform[:3])
            if any(abs(v)>1e7 for v in xyz) or scale>1e5:skipped+=1;continue
            base=records.get(link(items,b"NAME",p.slots))
            if base and base[0]==b"LIGH":
                spec=light(base[1]);light_count+=1
                if not spec or spec["flags"]&0x20:continue
                radius_override=floats(one(items,b"XRDS",4),1)
                radius=(radius_override[0] if radius_override and radius_override[0]>0 else spec["radius"])/units
                if not .1<=radius<=10000:continue
                x,y,z=transform[3:]
                direction=(sin(y)*sin(x)*cos(z)-cos(x)*sin(z),sin(y)*sin(x)*sin(z)+cos(x)*cos(z),cos(y)*sin(x)) if spec["kind"] else None
                # Photometric lumens converted to a bounded preview intensity, not game exposure.
                intensity=min(8.,max(.05,spec["lumen"]/1000.)) if spec["lumen"] else 1.
                lights.append(asdict(LocalLight(position=xyz,color=spec["color"],radius=radius,intensity=intensity,direction=direction,cone=max(5.,min(120.,spec["fov"])) if direction else 45.,shadows=spec["kind"]==1).validate()))
                continue
            asset="proxy"
            if base:
                model=string(one(base[1],b"MODL"))
                if model:
                    models.add(model)
                    if meshes is not None and model not in failed:
                        candidate="sf:"+model.replace("\\","/").casefold()
                        try:
                            if candidate not in assets:
                                imported=meshes(model)
                                if imported:
                                    m,lods=imported;assets[candidate]=m
                                    for i,lod in enumerate(lods,1):assets[candidate+"@lod"+str(i)]=lod
                            if candidate in assets:asset=candidate;model_count+=1
                        except (ValueError,OSError) as exc:
                            failed.add(model);issues.append(model+": "+str(exc)[:120])
            placed.append(Instance(label(rid),asset,*xyz,degrees(transform[5]),scale))
        # Include light positions as selection markers only where no geometry exists.
        if not placed and lights:
            placed=[Instance("light-"+str(i),"proxy",*row["position"],scale=.5) for i,row in enumerate(lights[:MAX_REFS])]
        scene=Scene(assets,placed)
        return scene,dict(cell=label(key),cells=1,grid=None,land_tiles=0,proxy_references=len(placed)-model_count,model_references=model_count,skipped_references=skipped,origin_game_units=(0,0,0),units_per_preview_unit=units,environment={},render_preview=dict(effects=fx,lights=lights,water_level=level),starfield=True,model_paths=sorted(models),light_records=light_count,issues=issues+["Starfield experimental: explicit mesh mapping only; no native NIF or planet terrain decoder"])
