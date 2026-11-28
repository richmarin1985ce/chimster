"""Read-only New Vegas LIGH, CELL/LGTM and WATR preview adapters.

Documented FNV layouts only; no native record writes. Units are converted
from game units to the viewport's 128-unit scale.
"""
import struct
from dataclasses import asdict,replace
from math import isfinite,dist,sin,cos
from .render_effects import LocalLight

def one(parts,tag,size):
    hits=[raw for t,raw in parts if t==tag and len(raw)==size]
    return hits[0] if len(hits)==1 else None

def rgba(raw):
    return tuple(v/255 for v in raw[:3])

def light_data(parts):
    raw=one(parts,b"DATA",32)
    if raw is None:return None
    _,radius,r,g,b,_,flags,falloff,fov,_,_=struct.unpack("<iI4BIffIf",raw)
    fade=one(parts,b"FMAM",4)
    fade=struct.unpack("<f",fade)[0] if fade is not None else 1.
    if not radius or not all(isfinite(v) for v in (fade,falloff,fov)):return None
    return dict(radius=radius,color=(r/255,g/255,b/255),flags=flags,fade=fade,falloff=falloff,fov=fov)

def lighting(raw):
    if raw is None or len(raw)!=40:return {}
    near,far,xy,z,fade,clip,power=struct.unpack_from("<2f2i3f",raw,12)
    if not all(isfinite(x) for x in (near,far,fade,clip,power)):return {}
    return dict(ambient=rgba(raw),sun_color=rgba(raw[4:]),fog_color=rgba(raw[8:]),fog_near=near,fog_far=far,rotation=(xy,z),sun_fade=fade,fog_clip=clip,fog_power=power)

def water_data(parts):
    flags=one(parts,b"FNAM",1);opacity=one(parts,b"ANAM",1)
    raw=one(parts,b"DNAM",196)
    if raw is None:
        legacy=one(parts,b"DATA",198);raw=legacy[:196] if legacy is not None else None
    result={}
    if flags is not None:result["reflective"]=bool(flags[0]&2)
    if opacity is not None:result["opacity"]=opacity[0]/255
    if raw is not None:
        refl=struct.unpack_from("<f",raw,20)[0]
        if isfinite(refl):result["reflectivity"]=max(0.,min(1.,refl))
        result.update(shallow=rgba(raw[40:44]),deep=rgba(raw[44:48]),reflection_color=rgba(raw[48:52]))
        amount,near,far=struct.unpack_from("<3f",raw,140)
        if all(isfinite(x) for x in (amount,near,far)) and far>near>=0:
            result["underwater_density"]=max(0.,min(1.,2.3*max(0.,amount)*128/max(1.,far-near)))
    return result

def decode(signature,parts,slots):
    if signature=="LIGH":
        data=light_data(parts);return {"native_light":data} if data else {}
    if signature=="WATR":return {"native_water":water_data(parts)}
    if signature=="LGTM":return {"native_lighting":lighting(one(parts,b"DATA",40))}
    if signature!="CELL":return {}
    data=one(parts,b"DATA",1);height=one(parts,b"XCLW",4)
    level=struct.unpack("<f",height)[0] if height is not None else None
    if level is not None and (not isfinite(level) or abs(level)>1e7):level=None
    links={}
    for name,tag in (("water",b"XCWT"),("template",b"LTMP")):
        raw=one(parts,tag,4)
        if raw is not None:
            key=slots.decode(struct.unpack("<I",raw)[0])
            if key is not None:links[name]=(key.origin,key.local)
    mask=one(parts,b"LNAM",4)
    return {"native_cell_render":dict(has_water=bool(data[0]&2) if data is not None else None,water_height=level,lighting=lighting(one(parts,b"XCLL",40)),inherit=struct.unpack("<I",mask)[0] if mask else 0,**links)}

def identity(pair):
    from .record_graph import Identity
    return Identity(*pair) if pair else None

def report(browser,cell,refs,origin,units,environment):
    if browser.profile!="new-vegas":return {}
    cellfx=cell.get("native_cell_render",{})
    light=cellfx.get("lighting",{}).copy()
    template=browser.active.get(identity(cellfx.get("template")),{}).get("native_lighting",{})
    for name,bit in (("ambient",1),("sun_color",2),("fog_color",4),("fog_near",8),("fog_far",16),("rotation",32),("sun_fade",64),("fog_clip",128),("fog_power",256)):
        if cellfx.get("inherit",0)&bit:
            if name in template:light[name]=template[name]
            else:light.pop(name,None)
    values={}
    if "ambient" in light:values["ambient"]=sum(light["ambient"])/3
    for key in ("sun_color","fog_color"):
        if key in light:values[key]=light[key]
    if light.get("fog_far",0)>max(0.,light.get("fog_near",0)):
        values["fog_density"]=min(1.,2.3*units/max(1.,light["fog_far"]-light.get("fog_near",0)))
    if "sun_fade" in light:values["sun_intensity"]=max(0.,min(4.,light["sun_fade"]))
    world=environment.get("values",{})
    water_key=cellfx.get("water") or world.get("water")
    height=cellfx.get("water_height")
    if height is None and world.get("heights"):height=world["heights"][1]
    enabled=cellfx.get("has_water")
    water_level=height/units if height is not None and (enabled is True or enabled is None and water_key) and abs(height)<1e7 else None
    if water_level is not None:
        wat=browser.active.get(identity(water_key),{}).get("native_water",{})
        for source,target in (("shallow","water_color"),("deep","water_deep_color"),("opacity","water_opacity"),("reflectivity","water_reflectivity"),("underwater_density","underwater_density")):
            if source in wat:values[target]=wat[source]
        if wat.get("reflective") is False:values["water_reflectivity"]=0.
    lights=[]
    for ref in refs:
        base=browser.active.get(ref.get("base"),{})
        raw=base.get("native_light")
        pos=ref.get("position")
        if not raw or pos is None or ref.get("flags",0)&0x800 or raw["flags"]&0x24:continue
        radius=raw["radius"]*ref.get("scale",1.)/units
        position=tuple((v-o)/units for v,o in zip(pos,origin))
        if radius<.1 or radius>10000 or any(abs(v)>1e7 for v in position):continue
        direction=None
        if raw["flags"]&0x600:
            # Approximate Bethesda Euler orientation using a forward +Y axis.
            x,y,z=ref.get("rotation",(0.,0.,0.))
            direction=(sin(y)*sin(x)*cos(z)-cos(x)*sin(z),sin(y)*sin(x)*sin(z)+cos(x)*cos(z),cos(y)*sin(x))
        local=LocalLight(position=position,color=raw["color"],intensity=max(0.,min(8.,raw["fade"])),radius=radius,direction=direction,cone=max(5.,min(120.,raw["fov"])) if direction else 45.,shadows=bool(direction and raw["flags"]&0x400))
        lights.append(asdict(local.validate()))
    return dict(effects=values,lights=lights,water_level=water_level,scope="FNV native read-only approximate preview; one selected-cell water plane")

def select_lights(rows,position,limit=4):
    ranked=sorted((LocalLight(**row).validate() for row in rows),key=lambda light:-(max(0.,1-dist(light.position,position)/light.radius)**2*light.intensity))
    result=[];shadow=False
    for light in ranked[:limit]:
        if light.shadows and shadow:light=replace(light,shadows=False)
        shadow=shadow or light.shadows
        result.append(light)
    return tuple(result)
