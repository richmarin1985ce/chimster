"""Shared opt-in preview effects; no renderer imports."""
from dataclasses import dataclass
from math import isfinite

def vector(v,n,lo,hi):
    if len(v)!=n or not all(isfinite(x) and lo<=x<=hi for x in v):
        raise ValueError("Invalid effect vector")

@dataclass(frozen=True)
class LocalLight:
    position:tuple=(0.,0.,5.)
    color:tuple=(1.,.8,.55)
    intensity:float=1.
    radius:float=12.
    direction:tuple=None
    cone:float=45.
    shadows:bool=False
    def validate(self):
        vector(self.position,3,-1e7,1e7)
        vector(self.color,3,0,1)
        if not isfinite(self.intensity) or not 0<=self.intensity<=8 or not isfinite(self.radius) or not .1<=self.radius<=10000:
            raise ValueError("Invalid local light")
        if self.direction is not None:
            vector(self.direction,3,-1e7,1e7)
            if not any(self.direction):raise ValueError("Zero spotlight direction")
        if not isfinite(self.cone) or not 5<=self.cone<=120:raise ValueError("Invalid spotlight cone")
        if self.shadows and self.direction is None:raise ValueError("Only spotlight shadows supported")
        return self

@dataclass(frozen=True)
class FogVolume:
    center:tuple=(0.,0.,0.)
    radius:float=8.
    density:float=.08
    def validate(self):
        vector(self.center,3,-1e7,1e7)
        if not isfinite(self.radius) or not .1<=self.radius<=10000 or not isfinite(self.density) or not 0<=self.density<=1:
            raise ValueError("Invalid fog volume")
        return self

@dataclass(frozen=True)
class Effects:
    shadow_size:int=0
    shadow_extent:float=48.
    shadow_cascades:int=1
    shadow_bias:float=.0015
    sun_color:tuple=(1.,1.,1.)
    ambient:float=.28
    sun_intensity:float=.72
    lights:tuple=()
    fog_density:float=0.
    fog_color:tuple=(.38,.48,.58)
    ao_strength:float=0.
    ao_radius:float=1.5
    scatter_strength:float=0.
    scatter_anisotropy:float=.55
    volume_steps:int=8
    volume_distance:float=160.
    fog_height:float=0.
    fog_falloff:float=0.
    fog_volumes:tuple=()
    water_level:float=None
    water_extent:float=32.
    water_color:tuple=(.05,.25,.31)
    reflection_size:int=0
    refraction:bool=False
    def validate(self):
        if self.volume_steps not in (4,8,16,24):raise ValueError("Invalid volume step count")
        if not isfinite(self.volume_distance) or not 1<=self.volume_distance<=10000:raise ValueError("Invalid volume distance")
        if not isfinite(self.fog_height) or abs(self.fog_height)>1e7 or not isfinite(self.fog_falloff) or not 0<=self.fog_falloff<=1:raise ValueError("Invalid height fog")
        if len(self.fog_volumes)>4:raise ValueError("At most four fog volumes")
        for volume in self.fog_volumes:volume.validate()
        if not isfinite(self.scatter_strength) or not 0<=self.scatter_strength<=2 or not isfinite(self.scatter_anisotropy) or not -.9<=self.scatter_anisotropy<=.9:
            raise ValueError("Invalid scattering parameters")
        if self.reflection_size not in (0,128,256,512):
            raise ValueError("Invalid reflection resolution")
        if self.refraction and not self.reflection_size:raise ValueError("Refraction requires water buffers")
        if self.shadow_cascades not in (1,2):raise ValueError("Invalid shadow cascade count")
        if not isfinite(self.shadow_bias) or not .00005<=self.shadow_bias<=.02:raise ValueError("Invalid shadow bias")
        vector(self.sun_color,3,0,1)
        if self.shadow_size not in (0,512,1024,2048):
            raise ValueError("Invalid shadow resolution")
        for value,lo,hi in ((self.shadow_extent,1,10000),(self.ambient,0,1),(self.sun_intensity,0,4),(self.fog_density,0,1),(self.ao_strength,0,1),(self.ao_radius,.05,20),(self.water_extent,1,10000)):
            if not isfinite(value) or not lo<=value<=hi:
                raise ValueError("Invalid effect setting")
        if self.water_level is not None and (not isfinite(self.water_level) or abs(self.water_level)>1e7):
            raise ValueError("Invalid water level")
        vector(self.fog_color,3,0,1);vector(self.water_color,3,0,1)
        if sum(bool(l.shadows) for l in self.lights)>1:raise ValueError("At most one local shadow map")
        if len(self.lights)>4:raise ValueError("At most four preview point lights")
        for light in self.lights:light.validate()
        return self

def preset(name):
    if name=="Off":return Effects()
    if name=="Low":return Effects(fog_density=.012,ao_strength=.3)
    if name=="Medium":return Effects(shadow_size=512,reflection_size=256,fog_density=.018,ao_strength=.45,scatter_strength=.35,volume_steps=8,fog_falloff=.015)
    if name=="High":return Effects(shadow_size=1024,shadow_cascades=2,reflection_size=512,refraction=True,fog_density=.022,ao_strength=.65,scatter_strength=.65,volume_steps=16,fog_falloff=.02)
    raise ValueError("Unknown effects preset")
