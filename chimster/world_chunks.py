"""Offline chunk store with bounded selective loading. Not yet wired into viewport."""
from pathlib import Path
from math import floor,isfinite
import json,hashlib
def build(placements,folder,size=128.):
    if not isfinite(size) or size<=0:raise ValueError("invalid chunk size")
    p=Path(folder);p.mkdir(parents=True,exist_ok=False);groups={};ids=set()
    for r in placements:
        i=r["id"];x,y=r["x_m"],r["y_m"]
        if not isinstance(i,str) or not i or i in ids or not all(isfinite(v) for v in (x,y)):raise ValueError("invalid or duplicate instance")
        ids.add(i);groups.setdefault((floor(x/size),floor(y/size)),[]).append(r)
    entries=[]
    for (x,y),rows in sorted(groups.items()):
        name=f"{x}_{y}.json";raw=json.dumps(rows,sort_keys=True,allow_nan=False).encode()
        (p/name).write_bytes(raw);entries.append({"x":x,"y":y,"file":name,"count":len(rows),"sha256":hashlib.sha256(raw).hexdigest()})
    manifest={"schema":1,"size":size,"count":len(ids),"chunks":entries}
    (p/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8");return manifest
def load(folder,x,y,radius=1):
    if type(radius) is not int or not 0<=radius<=16 or not all(isfinite(v) for v in (x,y)):raise ValueError("invalid query")
    p=Path(folder);mf=p/"manifest.json"
    if mf.stat().st_size>16*1024*1024:raise ValueError("manifest too large")
    m=json.loads(mf.read_text(encoding="utf-8"))
    if m["schema"]!=1 or not isfinite(m["size"]) or m["size"]<=0:raise ValueError("invalid manifest")
    a,b=floor(x/m["size"]),floor(y/m["size"]);rows=[];loaded=[]
    for e in m["chunks"]:
        if abs(e["x"]-a)>radius or abs(e["y"]-b)>radius:continue
        expected=f'{e["x"]}_{e["y"]}.json'
        if e["file"]!=expected or (p/expected).is_symlink() or (p/expected).stat().st_size>16*1024*1024:raise ValueError("invalid chunk path or size")
        data=(p/expected).read_bytes()
        if hashlib.sha256(data).hexdigest()!=e["sha256"]:raise ValueError("chunk digest mismatch")
        items=json.loads(data)
        if len(items)!=e["count"]:raise ValueError("chunk count mismatch")
        rows.extend(items);loaded.append(expected)
    return {"instances":rows,"loaded":loaded,"total_chunks":len(m["chunks"])}
