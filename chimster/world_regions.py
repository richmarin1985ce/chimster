"""FNV region settings, polygon queries and bounded native REGN encoding."""
import struct
from .fnv_patch import record,sub
from .fnv_world import cstr
from math import isfinite
from .record_graph import Identity
from .world_climate import validate as validate_climate

def validate(spec,index):
    world=Identity(*spec["world"])
    if world not in index.worlds:raise ValueError("Missing region worldspace")
    areas=[]
    for area in spec["areas"]:
        points=tuple(struct.unpack("<2f",struct.pack("<2f",*p)) for p in area["points"])
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
    map_name=spec.get("map_name","")
    if not isinstance(map_name,str) or "\0" in map_name or len(map_name.encode("cp1252"))>255:raise ValueError("Invalid map name")
    return {"world":(world.origin,world.local),"areas":areas,"weather":weather,"music":music,
            "color":color,"priority":priority,"map_name":map_name}

def contains(points,x,y):
    inside=False
    for a,b in zip(points,points[1:]+points[:1]):
        ax,ay=a;bx,by=b
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
    return inside

def at(regions,world,x,y):
    return sorted((r for r in regions if tuple(r["world"])==(world.origin,world.local) and any(contains(a["points"],x,y) for a in r["areas"])),key=lambda r:-r["priority"])

def encode(row,slots):
    spec=row["region_spec"]
    def fid(key):return struct.pack("<I",slots.encode(Identity(*key)))
    def header(kind):return sub(b"RDAT",struct.pack("<IBB2x",kind,1,spec["priority"]))
    body=sub(b"EDID",cstr(row["editor_id"]))+sub(b"RCLR",bytes(spec["color"]))+sub(b"WNAM",fid(spec["world"]))
    for area in spec["areas"]:
        body+=sub(b"RPLI",struct.pack("<I",area["falloff"]))
        body+=sub(b"RPLD",b"".join(struct.pack("<2f",*p) for p in area["points"]))
    if spec["weather"]:
        body+=header(3)+sub(b"RDWT",b"".join(fid(k)+struct.pack("<I",w)+(fid(g) if g else bytes(4)) for k,w,g in spec["weather"]))
    if spec["map_name"]:body+=header(4)+sub(b"RDMP",cstr(spec["map_name"]))
    if spec["music"]:body+=header(7)+sub(b"RDMO",fid(spec["music"]))
    return record(b"REGN",body,slots.encode(row["key"]))

def decode(parts,slots):
    spec={"areas":[],"weather":[],"music":None,"map_name":"","priority":0,"color":(128,160,128,255)}
    area=None;kind=None;priorities=[]
    def key(raw):
        k=slots.decode(struct.unpack("<I",raw)[0]);return (k.origin,k.local) if k else None
    for tag,raw in parts:
        if tag==b"WNAM" and len(raw)==4:spec["world"]=key(raw)
        elif tag==b"RCLR" and len(raw)==4:spec["color"]=tuple(raw)
        elif tag==b"RPLI" and len(raw)==4:
            area={"falloff":struct.unpack("<I",raw)[0],"points":()};spec["areas"].append(area)
        elif tag==b"RPLD" and area is not None and len(raw)%8==0:
            area["points"]=tuple(struct.iter_unpack("<2f",raw));area=None
        elif tag==b"RDAT":
            kind=None
            if len(raw)==8:
                kind,flags,priority=struct.unpack("<IBB2x",raw)
                if kind in (3,4,7):priorities.append(priority)
        elif tag==b"RDWT" and kind==3 and len(raw)%12==0:
            spec["weather"]=[(key(raw[i:i+4]),struct.unpack_from("<I",raw,i+4)[0],key(raw[i+8:i+12])) for i in range(0,len(raw),12)]
        elif tag==b"RDMP" and kind==4:spec["map_name"]=raw.rstrip(b"\0").decode("cp1252")
        elif tag==b"RDMO" and kind==7 and len(raw)==4:spec["music"]=key(raw)
    if not spec.get("world") or any(len(a["points"])<3 for a in spec["areas"]):return None
    spec["priority"]=max(priorities,default=0)
    return spec
