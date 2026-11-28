"""Versioned standalone Asset Forge project; portable geometry and material bindings."""
import json
from pathlib import Path
from .flora import Mesh
from .asset_forge import Session
from .modern_nif import texture_path

MAX_BYTES=64*1024*1024

def save(session,path):
    p=Path(path)
    if p.suffix.lower()!=".casset":raise ValueError("Expected .casset project")
    m=session.mesh
    data=json.dumps({"schema":1,"vertices":m.vertices,"uv":m.uv,"faces":m.faces,
                     "materials":session.materials},allow_nan=False,separators=(",",":")).encode("utf-8")
    if len(data)>MAX_BYTES:raise ValueError("Project exceeds size limit")
    with p.open("xb") as f:
        try:f.write(data)
        except OSError:
            f.close();p.unlink(missing_ok=True);raise

def load(path):
    p=Path(path)
    if p.suffix.lower()!=".casset" or not p.is_file() or p.stat().st_size>MAX_BYTES:raise ValueError("Expected bounded .casset project")
    try:
        d=json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(d,dict) or set(d)!={"schema","vertices","uv","faces","materials"} or type(d["schema"]) is not int or d["schema"]!=1:
            raise ValueError("Unsupported project schema")
        if not all(isinstance(d[k],list) for k in ("vertices","uv","faces")) or max(len(d[k]) for k in ("vertices","uv","faces"))>300000:
            raise ValueError("Invalid mesh arrays")
        if any(type(i) is not int for t,_ in d["faces"] for i in t):raise ValueError("Invalid index type")
        m=Mesh([tuple(v) for v in d["vertices"]],[tuple(v) for v in d["uv"]],[(tuple(t),mat) for t,mat in d["faces"]])
        s=Session(m);materials=d["materials"]
        if not isinstance(materials,dict) or set(materials)-set(s.groups()):raise ValueError("Unknown material bindings")
        for k,v in materials.items():
            if not isinstance(v,dict) or set(v)!={"diffuse","normal","cutout"} or type(v["cutout"]) is not bool or any(not isinstance(v[x],str) for x in ("diffuse","normal")):
                raise ValueError("Invalid material binding")
            s.materials[k]={"diffuse":texture_path(v["diffuse"]),"normal":texture_path(v["normal"]),"cutout":v["cutout"]}
        return s
    except (TypeError,KeyError,OverflowError) as e:raise ValueError("Malformed asset project") from e
