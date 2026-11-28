"""Portable region settings and point queries; native REGN export is separate."""
from math import isfinite
from .record_graph import Identity
from .world_climate import validate as validate_climate

def validate(spec,index):
    world=Identity(*spec["world"])
    if world not in index.worlds:raise ValueError("Missing region worldspace")
    areas=[]
    for area in spec["areas"]:
        points=tuple(tuple(p) for p in area["points"])
        if not 3<=len(points)<=2048 or len(set(points))!=len(points) or any(len(p)!=2 or not all(isfinite(v) and abs(v)<=1e9 for v in p) for p in points):
            raise ValueError("Invalid region polygon")
        if abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))<1:
            raise ValueError("Degenerate region polygon")
        falloff=area.get("falloff",0)
        if type(falloff)!=int or not 0<=falloff<=65535:raise ValueError("Invalid edge falloff")
        areas.append({"points":points,"falloff":falloff})
    if not 1<=len(areas)<=64:raise ValueError("Region requires 1–64 polygons")
    weather=validate_climate({"weather":spec["weather"]},index)["weather"] if spec.get("weather") else []
    color=tuple(spec.get("color",(128,160,128,255)))
    if len(color)!=4 or any(type(v)!=int or not 0<=v<=255 for v in color):raise ValueError("Invalid map color")
    priority=spec.get("priority",0)
    if type(priority)!=int or not 0<=priority<=255:raise ValueError("Invalid priority")
    music=spec.get("music")
    if music:
        key=Identity(*music)
        if index.active.get(key,{}).get("signature")!="MUSC":raise ValueError("Invalid music record")
        music=(key.origin,key.local)
    return {"world":(world.origin,world.local),"areas":areas,"weather":weather,"music":music,
            "color":color,"priority":priority,"map_name":str(spec.get("map_name",""))[:255]}

def contains(points,x,y):
    inside=False
    for a,b in zip(points,points[1:]+points[:1]):
        ax,ay=a;bx,by=b
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
    return inside

def at(regions,world,x,y):
    return sorted((r for r in regions if tuple(r["world"])==(world.origin,world.local) and any(contains(a["points"],x,y) for a in r["areas"])),key=lambda r:-r["priority"])
