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
    def validate(self):
        vector(self.position,3,-1e7,1e7)
        vector(self.color,3,0,1)
        if not isfinite(self.intensity) or not 0<=self.intensity<=8 or not isfinite(self.radius) or not .1<=self.radius<=10000:
            raise ValueError("Invalid local light")
        return self

@dataclass(frozen=True)
class Effects:
    shadow_size:int=0
    shadow_extent:float=48.
    ambient:float=.35
    sun_intensity:float=.8
    lights:tuple=()
    fog_density:float=0.
    fog_color:tuple=(.38,.48,.58)
    ao_strength:float=0.
    ao_radius:float=1.5
    scatter_strength:float=0.
    scatter_anisotropy:float=.55
    water_level:float=None
    water_extent:float=32.
    water_color:tuple=(.05,.25,.31)
    def validate(self):
        if not isfinite(self.scatter_strength) or not 0<=self.scatter_strength<=2 or not isfinite(self.scatter_anisotropy) or not -.9<=self.scatter_anisotropy<=.9:
            raise ValueError("Invalid scattering parameters")
        if self.shadow_size not in (0,512,1024,2048):
            raise ValueError("Invalid shadow resolution")
        for value,lo,hi in ((self.shadow_extent,1,10000),(self.ambient,0,1),(self.sun_intensity,0,4),(self.fog_density,0,1),(self.ao_strength,0,1),(self.ao_radius,.05,20),(self.water_extent,1,10000)):
            if not isfinite(value) or not lo<=value<=hi:
                raise ValueError("Invalid effect setting")
        if self.water_level is not None and (not isfinite(self.water_level) or abs(self.water_level)>1e7):
            raise ValueError("Invalid water level")
        vector(self.fog_color,3,0,1);vector(self.water_color,3,0,1)
        if len(self.lights)>4:raise ValueError("At most four preview point lights")
        for light in self.lights:light.validate()
        return self

def preset(name):
    if name=="Off":return Effects()
    if name=="Low":return Effects(fog_density=.012,ao_strength=.3)
    if name=="Medium":return Effects(shadow_size=512,fog_density=.018,ao_strength=.45,scatter_strength=.35)
    if name=="High":return Effects(shadow_size=1024,fog_density=.022,ao_strength=.65,scatter_strength=.65)
    raise ValueError("Unknown effects preset")
