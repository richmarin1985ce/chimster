"""Independent FO3/FNV native static-object LOD build; bounded known NIF layouts."""
from pathlib import Path
from math import floor,cos,sin
from collections import defaultdict
from hashlib import sha256
import json,shutil
from .world_models import resolve_model,archive_stamp
from .archive_reader import directory,reader
from .compatibility_asset_lookup import normalize
from .fnv_lod_nif import read_static_groups,encode_groups,check
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
            if p.suffix.lower() not in (".bsa",".ba2"):raise ValueError("Expected BSA or BA2")
            stamp=archive_stamp(p);entries=directory(p)
            if archive_stamp(p)!=stamp:raise ValueError("Archive changed during indexing")
            self.layers.append((p,entries,stamp))
        if self.root is None and not self.layers:raise ValueError("Select source game assets")
    def get(self,model):
        name=model.replace("\\","/")
        if not name.lower().startswith(("meshes/","textures/")):name="meshes/"+name
        pieces=name.split("/")
        if any(not p or p in (".","..") or ":" in p or "\0" in p for p in pieces) or not name.lower().endswith((".nif",".dds")):raise ValueError("Unsafe asset path")
        key=normalize(name)
        if self.root is not None:
            path=self.root
            for part in pieces:
                matches=[p for p in path.iterdir() if p.name.casefold()==part.casefold()] if path.is_dir() else []
                if not matches:break
                if len(matches)!=1:raise ValueError("Ambiguous loose asset")
                path=matches[0].resolve(strict=True)
                if not path.is_relative_to(self.root):raise ValueError("Asset escapes Data directory")
            else:
                if not path.is_file() or path.stat().st_size>64*1024*1024:raise ValueError("Asset size limit")
                return path.read_bytes()
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

def export(browser,world,output,assets,limit=512,previous=None,atlas=True):
    if browser.profile not in ("new-vegas","fallout3","skyrim","skyrim-se","fallout4"):raise ValueError("Native object LOD profile not supported")
    modern=browser.profile in ("skyrim","skyrim-se","fallout4")
    if modern:
        from .modern_lod_codec import read_static_groups as modern_read,encode_groups as modern_encode,inspect as modern_inspect
    def read(raw):return modern_read(raw,browser.profile) if modern else read_static_groups(raw,include_cutout=True)
    def encode_native(groups,kind):return modern_encode(groups,browser.profile,kind) if modern else encode_groups(groups,kind,16384 if kind=="object" else None)
    def inspect_native(raw,count):
        result=modern_inspect(raw,browser.profile) if modern else check(raw,count)
        if result["triangles"]!=count:raise ValueError("Geometry mismatch")
        return result
    name=world_name(browser,world)
    if not 1<=limit<=10000:raise ValueError("Invalid placement budget")
    refs=[]
    for r in browser.active.values():
        if r["signature"]!="REFR" or "position" not in r or r["flags"]&0x800 or r.get("enable_parent"):continue
        cell=browser.active.get(r.get("cell"),{})
        base=browser.active.get(r.get("base"),{})
        if cell.get("world")==world and base.get("signature") in (("STAT",) if modern else ("STAT","TREE")) and base.get("model"):
            refs.append((r,base))
    if len(refs)>limit:raise ValueError("Object placement budget exceeded; select a smaller world or raise limit")
    prior={};old_root=None
    if previous is not None:
        old_root=Path(previous).resolve(strict=True)
        manifest=json.loads((old_root/"manifest.json").read_text(encoding="utf-8"))
        if manifest.get("world")!=name:raise ValueError("Previous object package belongs to another world")
        prior={tuple(t["grid"]):t for t in manifest["tiles"]}
    output=Path(output);output.mkdir(exist_ok=False)
    report={"world":name,"profile":browser.profile,"external_tools":False,"native_runtime_assets":False,"companions":[],"tiles":[],"skipped":[],"atlas_issues":[],"reused_tiles":0,"rebuilt_tiles":0}
    cache={};tiles=defaultdict(dict)
    try:
        for ref,base in sorted(refs,key=lambda p:p[0]["key"]):
            model=base["model"];key=model.replace("\\","/").casefold()
            if key not in cache:
                try:
                    path=sibling(model)
                    generated=False
                    if modern:
                        # Prefer an explicit record-level LOD model where indexed; no classic _lod assumption.
                        chosen=base.get("lod_model")
                        raw=assets.get(chosen or model);generated=not chosen
                    else:
                        try:raw=assets.get(path)
                        except FileNotFoundError:
                            raw=assets.get(model);generated=True
                    groups=read(raw)
                    if generated:
                        groups=[(mesh if cut else reduced(mesh),d,n,cut) for mesh,d,n,cut in groups]
                        dest=output/path;dest.parent.mkdir(parents=True,exist_ok=True)
                        total=sum(len(mesh.faces) for mesh,*_ in groups)
                        if not modern:
                            raw=encode_native(groups,"companion");inspect_native(raw,total)
                            with dest.open("xb") as f:f.write(raw)
                            report["companions"].append({"path":path,"triangles":total,"sha256":sha256(raw).hexdigest()})
                    cache[key]=groups
                except (ValueError,OSError,TypeError,UnicodeError) as exc:
                    cache[key]=str(exc)[:200]
            value=cache[key]
            if isinstance(value,str):
                report["skipped"].append({"reference":label(ref["key"]),"reason":value});continue
            rx,ry,yaw=ref.get("rotation",(0,0,0))
            if abs(rx)>1e-6 or abs(ry)>1e-6:
                report["skipped"].append({"reference":label(ref["key"]),"reason":"Tilted placement not enabled"});continue
            px,py,pz=ref["position"];scale=ref.get("scale",1)
            from math import isfinite
            if not all(isfinite(v) for v in (px,py,pz,scale,yaw)) or not 0<scale<=100:
                report["skipped"].append({"reference":label(ref["key"]),"reason":"Invalid transform"});continue
            x,y=floor(px/16384)*4,floor(py/16384)*4
            groups=tiles[x,y]
            for mesh,d,n,cut in value:
                combined=groups.setdefault((d,n,cut),Mesh())
                if len(combined.vertices)+len(mesh.vertices)>65535 or len(combined.faces)+len(mesh.faces)>65535:
                    report["skipped"].append({"reference":label(ref["key"]),"reason":"16-bit group budget","material":d});continue
                offset=len(combined.vertices);c,s=cos(yaw),sin(yaw)
                combined.vertices.extend((px-x*4096+scale*(c*a-s*b),py-y*4096+scale*(s*a+c*b),pz+scale*z) for a,b,z in mesh.vertices)
                combined.uv.extend(mesh.uv)
                combined.faces.extend((tuple(i+offset for i in f),"lod") for f,_ in mesh.faces)
        for (x,y),groups in sorted(tiles.items()):
            active=[(m,*paths) for paths,m in sorted(groups.items()) if m.faces]
            if not active:continue
            path=f"meshes/landscape/lod/{name}/blocks/{name}.level4.x{x}.y{y}.nif"
            stem=f"textures/landscape/lod/{name}/blocks/{name}.level4.x{x}.y{y}"
            if modern:
                path=f"meshes/terrain/{name}/objects/{name}.4.{x}.{y}.bto"
                stem=f"textures/terrain/{name}/objects/{name}.4.{x}.{y}"
            texpaths=(stem+".dds",stem+"_n.dds")
            class CachedAssets:
                def __init__(self):self.raw={};self.hashes={};self.total=0
                def get(self,p):
                    if p not in self.raw:
                        if self.hashes.get(p)=="unavailable":raise ValueError("Unavailable source texture")
                        data=assets.get(p)
                        if self.total+len(data)>128*1024*1024:raise ValueError("Tile texture byte budget")
                        self.raw[p]=data;self.total+=len(data);self.hashes[p]=sha256(data).hexdigest()
                    return self.raw[p]
            source=CachedAssets()
            if atlas:
                for p in sorted({p for _,d,n,cut in active if not cut for p in (d,n)}):
                    try:source.get(p)
                    except (ValueError,OSError):source.hashes[p]="unavailable"
            digest=sha256(json.dumps(["object-lod-v5",browser.profile,name,x,y,atlas,[(m.vertices,m.uv,m.faces,d,n,cut) for m,d,n,cut in active],sorted(source.hashes.items())],separators=(",",":"),allow_nan=False).encode()).hexdigest()
            cached=prior.get((x,y),{})
            files=cached.get("files",{})
            if (cached.get("input_sha256")==digest and set(files) in ({path},{path,*texpaths})
                and all((old_root/p).is_file() and (old_root/p).resolve().is_relative_to(old_root) and sha256((old_root/p).read_bytes()).hexdigest()==files[p] for p in files)):
                for p in files:
                    (output/p).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old_root/p,output/p)
                report["tiles"].append(cached);report["reused_tiles"]+=1;continue
            atlas_info=None;written=[]
            if atlas:
                from .world_lod_atlas import build
                from .textures import mip_dds
                opaque=[(m,d,n) for m,d,n,cut in active if not cut]
                foliage=[g for g in active if g[3]]
                result,remaining,issues=build(opaque,source) if opaque else (None,[],[])
                report["atlas_issues"].extend({"grid":[x,y],**issue} for issue in issues)
                if result:
                    active=[(result["mesh"],*texpaths,False),*((m,d,n,False) for m,d,n in remaining),*foliage]
                    for p,normal,image in zip(texpaths,(False,True),(result["diffuse"],result["normal"])):
                        dest=output/p;dest.parent.mkdir(parents=True,exist_ok=True)
                        with dest.open("xb") as f:f.write(mip_dds(result["size"],result["size"],image,normal=normal))
                        written.append(p)
                    atlas_info={"size":result["size"],"groups":result["groups"],"source_hashes":result["source_hashes"]}
            raw=encode_native(active,"object")
            info=inspect_native(raw,sum(len(m.faces) for m,*_ in active))
            dest=output/path;dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open("xb") as f:f.write(raw)
            written.append(path)
            report["tiles"].append({"path":path,"grid":[x,y],**info,"sha256":sha256(raw).hexdigest(),"input_sha256":digest,"atlas":atlas_info,"files":{p:sha256((output/p).read_bytes()).hexdigest() for p in written}})
            report["rebuilt_tiles"]+=1
        report["scope"]="Experimental native object macro meshes; paired atlases for eligible opaque non-tiling material groups; other groups retain original texture references; runtime unverified."
        (output/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(output);raise
    return report
