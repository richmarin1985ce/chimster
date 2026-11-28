"""Independent FO3/FNV native static-object LOD build; bounded known NIF layouts."""
from pathlib import Path
from math import floor,cos,sin
from collections import defaultdict
from hashlib import sha256
import json,shutil
from .world_models import resolve_model,archive_stamp
from .archive_reader import directory,reader
from .compatibility_asset_lookup import normalize
from .fnv_lod_nif import read_static,encode_groups,encode,check
from .world_lod_objects import sibling
from .lod_assets import simplify
from .flora import Mesh
from .world_lod_native import world_name
from .world_browser import label

class Assets:
    """Explicit loose Data root and BSA layers. Later archive wins."""
    def __init__(self,root=None,archives=()):
        self.root=Path(root).resolve(strict=True) if root is not None else None
        self.layers=[]
        for p in archives:
            p=Path(p).resolve(strict=True)
            if p.suffix.lower()!=".bsa":raise ValueError("Expected classic BSA")
            stamp=archive_stamp(p);entries=directory(p)
            if archive_stamp(p)!=stamp:raise ValueError("Archive changed during indexing")
            self.layers.append((p,entries,stamp))
        if self.root is None and not self.layers:raise ValueError("Select source game assets")
    def get(self,model):
        name=model.replace("\\","/")
        if not name.lower().startswith("meshes/"):name="meshes/"+name
        key=normalize(name)
        if self.root is not None:
            try:path=resolve_model(self.root,name)
            except (ValueError,OSError):pass
            else:return path.read_bytes()
        for path,entries,stamp in reversed(self.layers):
            if key not in entries:continue
            if archive_stamp(path)!=stamp:raise ValueError("Archive changed")
            with path.open("rb") as f:raw=reader(f).read(f,entries[key],64*1024*1024)
            if archive_stamp(path)!=stamp:raise ValueError("Archive changed")
            return raw
        raise FileNotFoundError(name)

def reduced(mesh):
    extent=max(max(v[a] for v in mesh.vertices)-min(v[a] for v in mesh.vertices) for a in range(3))
    best=mesh
    if extent>0 and len(mesh.faces)>64:
        for d in (24,12,6):
            try:m=simplify(mesh,extent/d,8)
            except ValueError:continue
            if len(m.faces)<len(best.faces):best=m
    return best

def export(browser,world,output,assets,limit=512):
    if browser.profile not in ("new-vegas","fallout3"):raise ValueError("Native object LOD currently FO3/FNV only")
    name=world_name(browser,world)
    if not 1<=limit<=10000:raise ValueError("Invalid placement budget")
    refs=[]
    for r in browser.active.values():
        if r["signature"]!="REFR" or "position" not in r:continue
        cell=browser.active.get(r.get("cell"),{})
        base=browser.active.get(r.get("base"),{})
        if cell.get("world")==world and base.get("signature")=="STAT" and base.get("model"):
            refs.append((r,base))
    if len(refs)>limit:raise ValueError("Object placement budget exceeded; select a smaller world or raise limit")
    output=Path(output);output.mkdir(exist_ok=False)
    report={"world":name,"external_tools":False,"native_runtime_assets":False,"companions":[],"tiles":[],"skipped":[]}
    cache={};tiles=defaultdict(dict)
    try:
        for ref,base in sorted(refs,key=lambda p:p[0]["key"]):
            model=base["model"];key=model.replace("\\","/").casefold()
            if key not in cache:
                try:
                    path=sibling(model)
                    generated=False
                    try:raw=assets.get(path)
                    except FileNotFoundError:
                        raw=assets.get(model);generated=True
                    mesh,material=read_static(raw)
                    if generated:
                        mesh=reduced(mesh)
                        dest=output/path;dest.parent.mkdir(parents=True,exist_ok=True)
                        raw=encode(mesh,*material,"companion");check(raw,len(mesh.faces))
                        with dest.open("xb") as f:f.write(raw)
                        report["companions"].append({"path":path,"triangles":len(mesh.faces),"sha256":sha256(raw).hexdigest()})
                    cache[key]=(mesh,material)
                except (ValueError,OSError,TypeError,UnicodeError) as exc:
                    cache[key]=str(exc)[:200]
            value=cache[key]
            if isinstance(value,str):
                report["skipped"].append({"reference":label(ref["key"]),"reason":value});continue
            rx,ry,yaw=ref.get("rotation",(0,0,0))
            if abs(rx)>1e-6 or abs(ry)>1e-6:
                report["skipped"].append({"reference":label(ref["key"]),"reason":"Tilted placement not enabled"});continue
            mesh,material=value;px,py,pz=ref["position"];scale=ref.get("scale",1)
            x,y=floor(px/16384)*4,floor(py/16384)*4
            groups=tiles[x,y]
            combined=groups.setdefault(material,Mesh())
            if len(combined.vertices)+len(mesh.vertices)>65535 or len(combined.faces)+len(mesh.faces)>65535:
                report["skipped"].append({"reference":label(ref["key"]),"reason":"16-bit group budget"});continue
            offset=len(combined.vertices);c,s=cos(yaw),sin(yaw)
            combined.vertices.extend((px-x*4096+scale*(c*a-s*b),py-y*4096+scale*(s*a+c*b),pz+scale*z) for a,b,z in mesh.vertices)
            combined.uv.extend(mesh.uv)
            combined.faces.extend((tuple(i+offset for i in f),"lod") for f,_ in mesh.faces)
        for (x,y),groups in sorted(tiles.items()):
            active=[(m,*paths) for paths,m in sorted(groups.items()) if m.faces]
            if not active:continue
            raw=encode_groups(active,"object",16384)
            info=check(raw,sum(len(m.faces) for m,_,_ in active))
            path=f"meshes/landscape/lod/{name}/blocks/{name}.level4.x{x}.y{y}.nif"
            dest=output/path;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open("xb") as f:f.write(raw)
            report["tiles"].append({"path":path,"grid":[x,y],**info,"sha256":sha256(raw).hexdigest()})
        report["scope"]="Experimental native object macro meshes; original diffuse/normal references retained; no atlas or runtime validation."
        (output/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(output);raise
    return report
