"""Independent Skyrim traditional tree LOD LST/BTT and world atlas candidates.

Uses documented little-endian layout. Never modifies the shared Fallout atlas.
Input billboards and their game-unit dimensions are explicitly supplied by author.
"""
from collections import defaultdict
from pathlib import Path
from math import isfinite,floor,pi
import struct,json,shutil
from hashlib import sha256
from .atlas import Tile,pack
from .lod_dds import decode
from .texture_processing import dds
from .world_lod_native import world_name
from .world_browser import label
from .world_lod_atlas import resize

TYPE=struct.Struct("<I6fI")
REF=struct.Struct("<5f3I")

def encode_types(rows):
    if not 1<=len(rows)<=256:raise ValueError("Tree type limit")
    out=bytearray(struct.pack("<I",len(rows)))
    for i,row in enumerate(rows):
        index,w,h,u0,v0,u1,v1,unknown=row
        if index!=i or not all(isfinite(v) for v in (w,h,u0,v0,u1,v1)) or not 0<w<=1e6 or not 0<h<=1e6 or not 0<=u0<u1<=1 or not 0<=v0<v1<=1:raise ValueError("Invalid tree type")
        out.extend(TYPE.pack(*row))
    return bytes(out)

def decode_types(raw):
    if len(raw)<4:raise ValueError("Truncated tree list")
    n,=struct.unpack_from("<I",raw)
    if not 1<=n<=256 or len(raw)!=4+n*TYPE.size:raise ValueError("Invalid tree list size")
    rows=list(TYPE.iter_unpack(raw[4:]))
    encode_types(rows)
    return rows

def encode_tile(groups):
    if len(groups)>256:raise ValueError("Tree group limit")
    out=bytearray(struct.pack("<I",len(groups)));seen=set()
    for index,rows in sorted(groups.items()):
        if not 0<=index<256 or not 1<=len(rows)<=100000:raise ValueError("Invalid tree group")
        out.extend(struct.pack("<II",index,len(rows)))
        for row in rows:
            x,y,z,rot,scale,fid,u1,u2=row
            if not all(isfinite(v) and abs(v)<=1e9 for v in (x,y,z,rot,scale)) or not 0<=rot<=2*pi+1e-6 or not 0<scale<=100 or not 0<fid<=0xffffffff or fid in seen:raise ValueError("Invalid tree reference")
            seen.add(fid);out.extend(REF.pack(*row))
    return bytes(out)

def decode_tile(raw):
    if len(raw)<4:raise ValueError("Truncated tree tile")
    n,=struct.unpack_from("<I",raw);offset=4;groups={}
    if n>256:raise ValueError("Tree group limit")
    for _ in range(n):
        if offset+8>len(raw):raise ValueError("Truncated tree group")
        index,count=struct.unpack_from("<II",raw,offset);offset+=8
        end=offset+count*REF.size
        if index in groups or not 1<=count<=100000 or end>len(raw):raise ValueError("Invalid tree group")
        groups[index]=list(REF.iter_unpack(raw[offset:end]));offset=end
    if offset!=len(raw):raise ValueError("Trailing tree data")
    encode_tile(groups)
    return groups

def export(browser,world,output,spec,assets):
    if browser.profile not in ("skyrim","skyrim-se"):raise ValueError("Separate native tree tiles are supported only for Skyrim profiles; use object LOD for New Vegas")
    name=world_name(browser,world)
    origin=tuple(spec["southwest"])
    if len(origin)!=2 or any(type(v)!=int or not -32768<=v<=32767 for v in origin):raise ValueError("Use southwest origin from existing LODSettings")
    sources=getattr(browser,"source_paths",None)
    if not sources or len(sources)>254:raise ValueError("Explicit full-plugin load order required")
    order={p.name.casefold():i for i,p in enumerate(sources)}
    catalog=spec["billboards"]
    if not isinstance(catalog,dict) or not 1<=len(catalog)<=256:raise ValueError("Provide 1–256 billboards")
    size=spec.get("size",64)
    if size not in (64,128):raise ValueError("Unsupported billboard size")
    selected=[];skipped=[];used=set();local_ids=set()
    for r in sorted(browser.active.values(),key=lambda r:r["key"]):
        if r["signature"]!="REFR" or "position" not in r:continue
        cell=browser.active.get(r.get("cell"),{})
        base=browser.active.get(r.get("base"),{})
        if cell.get("world")!=world or base.get("signature") not in ("TREE","STAT"):continue
        key=label(base["key"])
        if key not in catalog:continue
        rx,ry,rz=r.get("rotation",(0,0,0));scale=r.get("scale",1)
        if r["flags"]&0x800 or r.get("enable_parent") or abs(rx)>1e-6 or abs(ry)>1e-6 or not 0<scale<=100:
            skipped.append({"reference":label(r["key"]),"reason":"Disabled, conditional or tilted reference"});continue
        identity=r["key"]
        if identity.origin not in order or not 0<identity.local<=0xffffff:raise ValueError("Invalid runtime FormID origin")
        if identity.local in local_ids:
            skipped.append({"reference":label(identity),"reason":"Duplicate local FormID; unloading may fail"});continue
        local_ids.add(identity.local);fid=order[identity.origin]<<24|identity.local
        x,y,z=r["position"];cx,cy=floor(x/4096),floor(y/4096)
        if cx<origin[0] or cy<origin[1]:raise ValueError("Reference outside southwest origin")
        tile=(origin[0]+(cx-origin[0])//4*4,origin[1]+(cy-origin[1])//4*4)
        selected.append((tile,key,(x,y,z,rz%(2*pi),scale,fid,0,0)));used.add(key)
    if not selected or len(selected)>250000:raise ValueError("Tree placement budget or no matching trees")
    types=[];tiles=[];hashes={}
    for i,key in enumerate(sorted(used)):
        entry=catalog[key];path=entry["texture"]
        if not path.replace("\\","/").lower().startswith("textures/"):raise ValueError("Expected relative texture path")
        raw=assets.get(path);image=decode(raw)
        if not any(a>0 for a in image[2][3::4]):raise ValueError("Empty tree billboard")
        tiles.append(Tile(str(i),size,size,resize(image,size)))
        types.append((key,float(entry["width"]),float(entry["height"])))
        hashes[key]=sha256(raw).hexdigest()
    side=128
    while (side//(size+8))**2<len(tiles):side*=2
    if side>4096:raise ValueError("Tree atlas size limit")
    pixels,layout=pack(tiles,side,side,4)
    rows=[];indices={}
    for i,(key,w,h) in enumerate(types):
        rect=layout[str(i)];indices[key]=i
        rows.append((i,w,h,rect["u0"],rect["v0"],rect["u1"],rect["v1"],0))
    groups=defaultdict(lambda:defaultdict(list))
    for tile,key,ref in selected:groups[tile][indices[key]].append(ref)
    out=Path(output);out.mkdir(exist_ok=False);files={}
    def save(path,raw):
        p=out/path;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open("xb") as f:f.write(raw)
        files[path]=sha256(raw).hexdigest()
    try:
        base=f"meshes/terrain/{name}/trees"
        raw=encode_types(rows);decode_types(raw);save(f"{base}/{name}.lst",raw)
        for (x,y),entries in sorted(groups.items()):
            raw=encode_tile(entries);decode_tile(raw);save(f"{base}/{name}.4.{x}.{y}.btt",raw)
        save(f"textures/terrain/{name}/trees/{name}TreeLOD.dds",dds(side,side,pixels,kind="BC3",alpha_coverage=True))
        report={"world":name,"southwest":origin,"load_order":list(order),"references":len(selected),"types":len(types),"tiles":len(groups),"skipped":skipped,"source_hashes":hashes,"files":files,"external_tools":False,"runtime_verified":False}
        (out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return report
