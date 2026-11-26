"""Explicit local tool bindings, fingerprint checks, and capability readiness.
Never downloads, launches, or silently substitutes a pinned executable."""
from pathlib import Path
import json,os,platform,sys,importlib.util
from .tooling import discover_tools
from .project import digest,atomic_json,read_json
REQUIREMENTS={
 "native_mesh":{"tools":["NIF bridge"],"modules":[]},
 "texture_compression":{"tools":["DirectXTex / texconv"],"modules":[]},
 "texture_editing":{"tools":[],"modules":["PIL"]},
 "gpu_viewport":{"tools":[],"modules":["moderngl"]},
 "version_control":{"tools":["Git"],"modules":[]},
 "archive_tools":{"tools":["BSArch / BSArchPro"],"modules":[]},
 "audio_conversion":{"tools":["FFmpeg"],"modules":[]},
 "papyrus_compile":{"tools":["Papyrus Compiler"],"modules":[]},
 "flash_tools":{"tools":["JPEXS"],"modules":[]},
}
def pin(path,tool,executable):
    known={r["name"] for r in discover_tools()}|{"NIF bridge","xEdit","GECK","Creation Kit"}
    if tool not in known:raise ValueError("unknown tool")
    p=Path(executable).expanduser().resolve(strict=True)
    if not p.is_file() or os.name!="nt" and not os.access(p,os.X_OK):raise ValueError("executable required")
    q=Path(path);data=read_json(q) if q.exists() else {"schema":1,"tools":{}}
    if data.get("schema")!=1 or not isinstance(data.get("tools"),dict):raise ValueError("invalid dependency config")
    data["tools"][tool]={"path":str(p),"sha256":digest(p)}
    q.parent.mkdir(parents=True,exist_ok=True);atomic_json(q,data)
    return data["tools"][tool]
def report(path=None):
    data=read_json(Path(path)) if path and Path(path).exists() else {"schema":1,"tools":{}}
    if data.get("schema")!=1 or not isinstance(data.get("tools"),dict):raise ValueError("invalid dependency config")
    result={r["name"]:{**r,"status":"discovered_unpinned" if r["path"] else "missing"} for r in discover_tools()}
    for k in ("NIF bridge","xEdit","GECK","Creation Kit"):result[k]={"name":k,"path":None,"status":"missing"}
    for k,v in data["tools"].items():
        if k not in result:raise ValueError("unknown pinned tool")
        p=Path(v["path"])
        try:
            ok=p.is_file() and (os.name=="nt" or os.access(p,os.X_OK)) and digest(p)==v["sha256"]
        except OSError:ok=False
        result[k]={"name":k,"path":str(p),"status":"pinned" if ok else "changed_or_missing"}
    modules={k:importlib.util.find_spec(k) is not None for k in ("PIL","moderngl")}
    capabilities={}
    for k,v in REQUIREMENTS.items():
        missing=[t for t in v["tools"] if result[t]["status"]!="pinned"]+[m for m in v["modules"] if not modules[m]]
        capabilities[k]={"ready":not missing,"unverified":missing}
    return {"platform":platform.system(),"python":sys.version.split()[0],"tools":list(result.values()),"modules":modules,"capabilities":capabilities,"scope":"presence and executable hash only; actual versions and runtime compatibility require tool tests"}
