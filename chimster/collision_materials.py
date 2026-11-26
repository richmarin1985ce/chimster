"""FO3/FNV collision materials and explicit compound box recipe."""
from pathlib import Path
import json,math
# NifTools Fallout3HavokMaterial numeric enum, distinct from Skyrim hashes.
BASE=("stone","cloth","dirt","glass","grass","metal","organic","skin","water","wood",
      "heavy_stone","heavy_metal","heavy_wood","chain","bottlecap","elevator","hollow_metal",
      "sheet_metal","sand","broken_concrete","vehicle_body","vehicle_part_solid","vehicle_part_hollow",
      "barrel","bottle","soda_can","pistol","rifle","shopping_cart","lunchbox","baby_rattle","rubber_ball")
MATERIALS={name+suffix:i+offset for i,name in enumerate(BASE) for suffix,offset in
           (("",0),("_platform",32),("_stairs",64),("_stairs_platform",96))}
def material_id(value,game):
    if game not in {"fallout3","newvegas"}:raise ValueError("collision material profile not implemented for this game")
    if type(value) is int and 0<=value<=127:return value
    if isinstance(value,str) and value in MATERIALS:return MATERIALS[value]
    raise ValueError("unknown FO3/FNV Havok material: "+str(value))
def validate(spec,game,scale=1):
    if not isinstance(spec,dict) or spec.get("kind")!="compound_aabb" or set(spec)-{"kind","boxes","list_material","status"}:raise ValueError("expected compound_aabb recipe")
    if not math.isfinite(scale) or not 0<scale<=100000:raise ValueError("invalid collision scale")
    boxes=spec["boxes"]
    if not isinstance(boxes,list) or not 1<=len(boxes)<=256:raise ValueError("expected 1..256 collision boxes")
    default=material_id(spec.get("list_material","stone"),game)
    rows=[];ids=set()
    for i,b in enumerate(boxes):
        if not isinstance(b,dict) or set(b)-{"id","min","max","material"}:raise ValueError("invalid collision box fields")
        name=b.get("id",str(i))
        if not isinstance(name,str) or not name or len(name)>100 or name in ids:raise ValueError("duplicate or invalid box ID")
        ids.add(name)
        a,c=b["min"],b["max"]
        if len(a)!=3 or len(c)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v*scale)>1e7 for v in (*a,*c)):raise ValueError("invalid box bounds")
        lo=tuple(v*scale for v in a);hi=tuple(v*scale for v in c)
        if any(y-x<.001 for x,y in zip(lo,hi)):raise ValueError("degenerate box")
        rows.append({"id":name,"min":lo,"max":hi,"material":material_id(b.get("material",default),game)})
    return default,rows
def exchange(spec,game,scale=1):
    default,rows=validate(spec,game,scale)
    lines=[f"CHIMSTER_COLLISION_1 {len(rows)} {default}"]
    for r in rows:lines.append(" ".join(format(v,".9g") for v in (*r["min"],*r["max"]))+" "+str(r["material"]))
    return "\n".join(lines)+"\n",default,[r["material"] for r in rows]
def load(path):
    p=Path(path)
    if p.stat().st_size>1024*1024:raise ValueError("collision recipe too large")
    return json.loads(p.read_text(encoding="utf-8"))
