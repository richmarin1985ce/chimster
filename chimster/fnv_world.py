"""Experimental masterless FNV worldspace fixture writer. No game assets needed.
Height encoding follows signed differential rows (8 game units per step).
Optional explicit static placements and base landscape layers; no engine verification."""
import struct,math,re
from pathlib import Path
from .fnv_records import HEADER,scan,subs
from .fnv_patch import sub,record
from .worldspace import Terrain

def encode_height(grid):
    if len(grid)!=33 or any(len(row)!=33 for row in grid):raise ValueError("expected 33x33")
    if any(not isinstance(v,int) for row in grid for v in row):raise ValueError("expected globally quantized height steps")
    base=grid[0][0];deltas=[]
    for y,row in enumerate(grid):
        for x,v in enumerate(row):
            prev=row[x-1] if x else grid[y-1][0] if y else base
            d=v-prev
            if not -128<=d<=127:raise ValueError(f"VHGT slope overflow at {x},{y}: {d}; change scale or resample explicitly")
            deltas.append(d)
    raw=struct.pack("<f1089b3x",base,*deltas)
    if decode_height(raw)!=grid:raise ValueError("height encoding lost precision")
    return raw

def decode_height(raw):
    if len(raw)!=1096:raise ValueError("invalid VHGT")
    base,*deltas=struct.unpack("<f1089b3x",raw)
    if not math.isfinite(base) or not base.is_integer():raise ValueError("expected integer fixture datum")
    rows=[]
    for y in range(33):
        row=[]
        for x in range(33):
            prev=row[-1] if x else rows[-1][0] if y else int(base)
            row.append(prev+deltas[y*33+x])
        rows.append(tuple(row))
    return tuple(rows)

def normals(grid,x0,y0):
    # Calculate from the global quantized grid so adjacent cell edges match.
    n=len(grid);raw=[]
    for y in range(y0,y0+33):
        for x in range(x0,x0+33):
            dx=(grid[y][min(n-1,x+1)]-grid[y][max(0,x-1)])*8/(128*(2 if 0<x<n-1 else 1))
            dy=(grid[min(n-1,y+1)][x]-grid[max(0,y-1)][x])*8/(128*(2 if 0<y<n-1 else 1))
            v=(-dx,-dy,1);l=math.sqrt(sum(z*z for z in v));raw.extend(round(127*z/l) for z in v)
    return struct.pack("<3267b",*raw)

def group(kind,label,body):
    if isinstance(label,int):label=struct.pack("<I",label)
    if len(label)!=4:raise ValueError("invalid group label")
    return struct.pack("<4sI4sIII",b"GRUP",24+len(body),label,kind,0,0)+body
def cstr(value):
    if not isinstance(value,str) or "\0" in value:raise ValueError("invalid string")
    return value.encode("cp1252")+b"\0"
def cell_record(id,x,y,persistent=False):
    body=sub(b"DATA",b"\0")+sub(b"XCLC",struct.pack("<iiI",x,y,0))
    return HEADER.pack(b"CELL",len(body),0x400 if persistent else 0,id,0,15,0)+body
def build(terrain,output,editor_id="ChimsterWorld",title="Chimster World",origin=(-4,-4),vertical_scale=1.,content=None):
    terrain.validate();p=Path(output)
    if p.suffix.lower()!=".esp" or p.exists() or p.is_symlink():raise ValueError("expected new ESP")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}",editor_id):raise ValueError("invalid editor ID")
    if not math.isfinite(vertical_scale) or not 0<vertical_scale<=100:raise ValueError("invalid vertical scale")
    ox,oy=origin;n=terrain.cells
    if any(not isinstance(v,int) or not -1024<=v<=1024-n for v in origin):raise ValueError("invalid origin")
    units_m=128/terrain.spacing_m
    q=tuple(tuple(round((v-terrain.datum_m)*units_m*vertical_scale/8) for v in row) for row in terrain.heights)
    error=max(abs((v-terrain.datum_m)*units_m*vertical_scale-q[y][x]*8) for y,row in enumerate(terrain.heights) for x,v in enumerate(row))
    world,persistent=0x800,0x801;next_id=0x802;blocks={};expected={}
    from .fnv_content import static,reference,textures,book_record
    from .books import Book
    from .world_tools import snap_placements
    from .land_layers import encode_layers
    from .land_paint import Paint
    content=content or {}
    if not isinstance(content,dict) or set(content)-{"statics","placements","textures","paint","alpha_layers","books"}:raise ValueError("unknown world content fields")
    top={};base_ids={};texture_ids={};placed={};ref_expected={};layer_expected={}
    ids={editor_id.casefold()}
    def register(name):
        if name.casefold() in ids:raise ValueError("duplicate editor ID")
        ids.add(name.casefold())
    for spec in content.get("statics",[]):
        register(spec["id"]);base_ids[spec["id"]]=next_id
        top.setdefault(b"STAT",[]).append(static(next_id,spec));next_id+=1
    for spec in content.get("textures",[]):
        register(spec["id"]);register(spec["id"]+"TX")
        tx,lt=textures(next_id,next_id+1,spec);texture_ids[spec["id"]]=next_id+1
        top.setdefault(b"TXST",[]).append(tx);top.setdefault(b"LTEX",[]).append(lt);next_id+=2
    for spec in content.get("books",[]):
        b=Book(**spec["book"]).validate();register(b.editor_id);base_ids[b.editor_id]=next_id
        sig,raw=book_record(next_id,b,spec.get("model"),spec.get("value",1),spec.get("weight",.2),skill=spec.get("skill",-1),untakeable=spec.get("untakeable",False))
        top.setdefault(sig,[]).append(raw);next_id+=1
    paint=None
    if "paint" in content:
        paint=Paint(tuple(tuple(r) for r in content["paint"])).validate(n)
        if any(v not in texture_ids for row in paint.rows for v in row):raise ValueError("unknown painted texture")
    if content.get("alpha_layers") and not paint:raise ValueError("alpha layers require base paint")
    alpha_layers=encode_layers(content.get("alpha_layers",[]),texture_ids,n)
    if len(content.get("placements",[]))>50000:raise ValueError("too many references")
    for spec in snap_placements(terrain,content.get("placements",[])):
        x,y,z=(spec[k] for k in ("x_m","y_m","z_m"))
        if not all(math.isfinite(v) for v in (x,y,z)):raise ValueError("invalid placement")
        gx,gy=ox*4096+x*units_m,oy*4096+y*units_m
        cx,cy=math.floor(gx/4096),math.floor(gy/4096)
        if not ox<=cx<ox+n or not oy<=cy<oy+n:raise ValueError("placement outside world")
        base=base_ids[spec["base"]];gz=(z-terrain.datum_m)*units_m*vertical_scale
        ref=reference(next_id,base,gx,gy,gz,spec.get("yaw",0),spec.get("scale",1))
        placed.setdefault((cx,cy),[]).append(ref);ref_expected[next_id]=base;next_id+=1
    record_count=2+sum(map(len,top.values()))+len(ref_expected);group_count=2+len(top)
    for y in range(n):
        for x in range(n):
            cx,cy=x+ox,y+oy;cid,lid=next_id,next_id+1;next_id+=2
            grid=tuple(tuple(row[x*32:x*32+33]) for row in q[y*32:y*32+33])
            body=sub(b"DATA",struct.pack("<I",3))+sub(b"VNML",normals(q,x*32,y*32))+sub(b"VHGT",encode_height(grid))+sub(b"VCLR",bytes([255])*3267)
            if paint:
                layers=tuple(texture_ids[k] for k in paint.quadrants(x,y))
                body+=b"".join(sub(b"BTXT",struct.pack("<IBBh",v,i,0,-1)) for i,v in enumerate(layers))
                layer_expected[lid]=layers
                body+=alpha_layers.get((x,y),b"")
            land=record(b"LAND",body,lid)
            cell=cell_record(cid,cx,cy)+group(6,cid,group(9,cid,land+b"".join(placed.get((cx,cy),[]))))
            blocks.setdefault((cy//32,cx//32),{}).setdefault((cy//8,cx//8),[]).append(cell)
            expected[lid]=grid;record_count+=2;group_count+=2
    children=cell_record(persistent,0,0,True)
    for block,subblocks in sorted(blocks.items()):
        body=b""
        for label,cells in sorted(subblocks.items()):
            body+=group(5,struct.pack("<hh",*label),b"".join(cells));group_count+=1
        children+=group(4,struct.pack("<hh",*block),body);group_count+=1
    wrld=sub(b"EDID",cstr(editor_id))+sub(b"FULL",cstr(title))+sub(b"PNAM",b"\0\0")+sub(b"DNAM",struct.pack("<ff",0,-10000))+sub(b"ONAM",struct.pack("<fff",1,0,0))+sub(b"DATA",b"\x12")+sub(b"NAM0",struct.pack("<ff",ox,oy))+sub(b"NAM9",struct.pack("<ff",ox+n-1,oy+n-1))+sub(b"NNAM",b"\0")+sub(b"XNAM",b"\0")
    data=group(0,b"WRLD",record(b"WRLD",wrld,world)+group(1,world,children))
    data=b"".join(group(0,sig,b"".join(top[sig])) for sig in (b"TXST",b"LTEX",b"BOOK",b"STAT",b"NOTE") if sig in top)+data
    header=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,record_count+group_count,next_id))+sub(b"CNAM",b"Chimster\0")+sub(b"SNAM",b"Experimental terrain fixture; not engine validated\0"))
    with p.open("xb") as f:f.write(header+data)
    try:
        check=scan(p)
        counts={k:sum(r["signature"]==k for r in check["records"]) for k in ("WRLD","CELL","LAND")}
        extra={k.decode():len(v) for k,v in top.items()}
        if ref_expected:extra["REFR"]=len(ref_expected)
        if counts!={"WRLD":1,"CELL":n*n+1,"LAND":n*n}:raise ValueError("record count mismatch")
        if any(sum(r["signature"]==k for r in check["records"])!=v for k,v in extra.items()):raise ValueError("content count mismatch")
        counts.update(extra)
        with p.open("rb") as f:
            for r in check["records"]:
                if r["signature"] not in ("LAND","REFR"):continue
                f.seek(r["offset"]);_,size,*_=HEADER.unpack(f.read(24));parts=list(subs(f.read(size)));fields=dict(parts)
                if r["signature"]=="REFR":
                    if struct.unpack("<I",fields[b"NAME"])[0]!=ref_expected[r["local_id"]]:raise ValueError("base reference mismatch")
                    continue
                if decode_height(fields[b"VHGT"])!=expected[r["local_id"]]:raise ValueError("height roundtrip mismatch")
                if r["local_id"] in layer_expected:
                    found=tuple(struct.unpack("<IBBh",v)[0] for k,v in parts if k==b"BTXT")
                    if found!=layer_expected[r["local_id"]]:raise ValueError("land texture mismatch")
    except Exception:
        p.unlink();raise
    from .world_validator import validate
    try:
        validation=validate([p])
        if not validation["valid"]:raise ValueError("worldspace validation failed: "+str(validation["issues"][:5]))
    except Exception:
        p.unlink();raise
    return {"output":str(p),"records":counts,"origin":list(origin),"cells_per_axis":n,"source_spacing_m":terrain.spacing_m,"horizontal_units_per_m":units_m,"vertical_scale":vertical_scale,"datum_m":terrain.datum_m,"max_quantization_error_game_units":error,"status":"experimental masterless ESP; self-reader verified, not validated in xEdit or game"}
