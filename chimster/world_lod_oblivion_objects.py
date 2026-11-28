"""Original TES4 DistantLOD placement and CMP cell-index codecs.

Only explicitly eligible, existing _far.nif models are referenced. The base
FormID depends on load order. No source assets are modified or deleted.
"""
import struct,json,shutil
from pathlib import Path
from math import floor,isfinite
from collections import defaultdict
from hashlib import sha256
from .world_lod_native import world_name
from .world_browser import label

def encode_cell(groups):
    if not 1<=len(groups)<=65535:raise ValueError("DistantLOD group limit")
    out=bytearray(struct.pack("<I",len(groups)))
    for fid,refs in sorted(groups.items()):
        if not 0<fid<=0xffffffff or not 1<=len(refs)<=100000:raise ValueError("Invalid distant group")
        for pos,rot,scale in refs:
            if len(pos)!=3 or len(rot)!=3 or not all(isfinite(v) for v in (*pos,*rot,scale)) or not 0<scale<=100:raise ValueError("Invalid distant transform")
        out.extend(struct.pack("<II",fid,len(refs)))
        for pos,_,_ in refs:out.extend(struct.pack("<3f",*(round(p)+offset for p,offset in zip(pos,(.5,.5,.970703125)))))
        for _,rot,_ in refs:out.extend(struct.pack("<3f",*rot))
        for _,_,scale in refs:out.extend(struct.pack("<f",round(scale,2)*100+.970001220703))
    return bytes(out)

def decode_cell(raw):
    if len(raw)<4:raise ValueError("Truncated distant cell")
    n,=struct.unpack_from("<I",raw)
    if not 1<=n<=65535:raise ValueError("Distant group limit")
    offset=4;out={}
    for _ in range(n):
        if offset+8>len(raw):raise ValueError("Truncated group")
        fid,count=struct.unpack_from("<II",raw,offset);offset+=8
        end=offset+28*count
        if fid in out or not fid or not 1<=count<=100000 or end>len(raw):raise ValueError("Invalid group")
        pos=list(struct.iter_unpack("<3f",raw[offset:offset+12*count]))
        rot=list(struct.iter_unpack("<3f",raw[offset+12*count:offset+24*count]))
        scale=[v[0] for v in struct.iter_unpack("<f",raw[offset+24*count:end])]
        if not all(isfinite(v) for p,r,s in zip(pos,rot,scale) for v in (*p,*r,s)) or any(s<=0 for s in scale):raise ValueError("Invalid stored transform")
        out[fid]=list(zip(pos,rot,scale));offset=end
    if offset!=len(raw):raise ValueError("Trailing distant data")
    return out

def encode_index(cells):
    cells=sorted(set(cells))
    if any(not -32768<=x<=32767 or not -32768<=y<=32767 for x,y in cells):raise ValueError("CMP coordinate limit")
    return b"".join(struct.pack("<hh",y,x) for x,y in cells)+struct.pack("<I",7)

def decode_index(raw):
    if len(raw)<4 or len(raw)%4 or raw[-4:]!=struct.pack("<I",7):raise ValueError("Invalid CMP trailer")
    cells=[(x,y) for y,x in struct.iter_unpack("<hh",raw[:-4])]
    if len(set(cells))!=len(cells):raise ValueError("Duplicate CMP cell")
    return cells

def far_path(model):
    model=model.replace("\\","/")
    if not model.lower().startswith("meshes/"):model="meshes/"+model
    if not model.lower().endswith(".nif") or any(p in ("",".","..") or ":" in p for p in model.split("/")):raise ValueError("Unsafe source model")
    return model[:-4]+"_far.nif"

def export(browser,world,output,assets):
    if browser.profile!="oblivion":raise ValueError("Oblivion only")
    name=world_name(browser,world)
    sources=getattr(browser,"source_paths",None)
    if not sources or len(sources)>254:raise ValueError("Explicit full-plugin load order required")
    order={p.name.casefold():i for i,p in enumerate(sources)}
    cells=defaultdict(lambda:defaultdict(list));skipped=[];checked={}
    for ref in sorted(browser.active.values(),key=lambda r:r["key"]):
        if ref["signature"]!="REFR" or "position" not in ref:continue
        cell=browser.active.get(ref.get("cell"),{})
        base=browser.active.get(ref.get("base"),{})
        if cell.get("world")!=world or not base.get("model"):continue
        if ref["flags"]&0x800 or ref.get("enable_parent"):continue
        # Require Visible When Distant on either winning base or placed reference.
        if not (base["flags"]|ref["flags"])&0x8000:continue
        model=base["model"];key=model.casefold()
        if key not in checked:
            try:
                path=far_path(model);raw=assets.get(path)
                if not raw.startswith(b"Gamebryo File Format, Version 20.0.0.5\n"):raise ValueError("Not an Oblivion far mesh")
                checked[key]=(path,sha256(raw).hexdigest())
            except (ValueError,OSError) as exc:checked[key]=str(exc)
        if isinstance(checked[key],str):
            skipped.append({"reference":label(ref["key"]),"reason":checked[key]});continue
        b=base["key"]
        if b.origin not in order or not 0<b.local<=0xffffff:raise ValueError("Invalid base identity")
        fid=order[b.origin]<<24|b.local
        pos=ref["position"];rot=ref.get("rotation",(0,0,0));scale=ref.get("scale",1)
        if not all(isfinite(v) for v in (*pos,*rot,scale)) or not 0<scale<=100 or any(abs(v)>1e7 for v in pos):raise ValueError("Invalid placed transform")
        x,y=(floor((round(v)+.5)/4096) for v in pos[:2])
        cells[x,y][fid].append((pos,rot,scale))
        if sum(map(len,cells[x,y].values()))>100000:raise ValueError("Cell placement budget")
    if not cells:raise ValueError("No supported VWD references with existing far meshes")
    out=Path(output);out.mkdir(exist_ok=False);files={}
    try:
        folder=out/"DistantLOD";folder.mkdir()
        for (x,y),groups in sorted(cells.items()):
            raw=encode_cell(groups);decoded=decode_cell(raw)
            if sum(map(len,decoded.values()))!=sum(map(len,groups.values())):raise ValueError("Placement roundtrip mismatch")
            p=folder/f"{name}_{x}_{y}.lod";p.write_bytes(raw);files[str(p.relative_to(out))]=sha256(raw).hexdigest()
        raw=encode_index(cells)
        if set(decode_index(raw))!=set(cells):raise ValueError("CMP roundtrip mismatch")
        p=folder/f"{name}.cmp";p.write_bytes(raw);files[str(p.relative_to(out))]=sha256(raw).hexdigest()
        report={"world":name,"load_order":list(order),"cells":len(cells),
                "references":sum(len(refs) for groups in cells.values() for refs in groups.values()),
                "far_meshes":{k:v for k,v in checked.items() if not isinstance(v,str)},"skipped":skipped,
                "files":files,"external_tools":False,"runtime_verified":False}
        (out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return report
