"""Prepare FNV/FO3 static object LOD candidates without modifying source assets."""
from pathlib import Path
from math import isfinite
from .world_browser import label
from .lod_assets import simplify
from .flora import write_obj
from .world_models import resolve_model
import json,shutil

def sibling(model):
    parts=model.replace("\\","/").split("/")
    if parts and parts[0].casefold()=="meshes":parts=parts[1:]
    if not parts or any(not p or p in (".","..") or ":" in p or "\0" in p for p in parts) or not parts[-1].lower().endswith(".nif"):
        raise ValueError("Unsafe static model path")
    return "meshes/"+"/".join(parts)[:-4]+"_lod.nif"

def candidates(browser,world):
    if world not in browser.worlds:raise ValueError("Select worldspace")
    models={}
    for row in browser.active.values():
        if row["signature"]!="REFR" or "position" not in row:continue
        parent=browser.active.get(row.get("cell"),{})
        if parent.get("world")!=world:continue
        base=browser.active.get(row.get("base"),{})
        if base.get("signature")!="STAT" or not base.get("model"):continue
        try:path=sibling(base["model"])
        except ValueError:continue
        group=models.setdefault(path.casefold(),{"model":base["model"],"sibling":path,"bases":set(),"references":0})
        group["bases"].add(label(base["key"]));group["references"]+=1
    return [{**v,"bases":sorted(v["bases"])} for k,v in sorted(models.items())]

def export(browser,world,output,models,loose_root=None,limit=128):
    if browser.profile not in ("new-vegas","fallout3"):raise ValueError("Classic object LOD only")
    rows=candidates(browser,world)
    if not 1<=limit<=512:raise ValueError("Invalid object budget")
    out=Path(output);out.mkdir(exist_ok=False)
    report={"world":label(world),"models":[],"native_runtime_assets":False}
    try:
        for row in rows[:limit]:
            entry=dict(row)
            if loose_root is not None:
                try:resolve_model(loose_root,row["sibling"])
                except (OSError,ValueError):pass
                else:
                    entry["status"]="Existing loose LOD sibling";report["models"].append(entry);continue
            try:
                mesh=models(row["model"])
                extent=max(max(v[a] for v in mesh.vertices)-min(v[a] for v in mesh.vertices) for a in range(3))
                if not isfinite(extent) or extent<=0:raise ValueError("Invalid model extent")
                proxy=mesh
                for divisor in (24,12,6):
                    try:candidate=simplify(mesh,extent/divisor,8)
                    except ValueError:continue
                    if len(candidate.faces)<len(proxy.faces):proxy=candidate
                if len(proxy.faces)>=len(mesh.faces):raise ValueError("No useful simplification")
                file=Path(row["sibling"]).with_suffix(".obj")
                dest=out/file;dest.parent.mkdir(parents=True,exist_ok=True)
                write_obj(proxy,dest)
                entry.update(status="Portable candidate",file=file.as_posix(),source_triangles=len(mesh.faces),lod_triangles=len(proxy.faces))
            except (ValueError,OSError,TypeError,RuntimeError,ImportError,AttributeError) as exc:entry.update(status="Skipped",reason=str(exc)[:200])
            report["models"].append(entry)
        report["unprocessed"]=max(0,len(rows)-limit)
        (out/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(out);raise
    return report
