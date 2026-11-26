"""MIT bridge client: typed text mesh exchange, optional separately built GPL helper."""
from pathlib import Path
import math,json,tempfile,subprocess,re,shutil
from .flora import cross
from .lod import validate_mesh
GAMES={"fallout3","newvegas","skyrim","skyrimse","skyrimvr","fallout4","fallout4vr"}

def texture_path(value):
    if not value:return ""
    if not isinstance(value,str) or not value.isascii():raise ValueError("texture path must be ASCII")
    p=value.replace("\\","/").split("/")
    if len(p)<2 or p[0].casefold()!="textures" or any(not re.fullmatch(r"[A-Za-z0-9_. -]+",s) or s in (".","..") for s in p) or not p[-1].lower().endswith(".dds"):raise ValueError("expected safe textures/*.dds path")
    return "\\".join(p)
def mesh_exchange(mesh,materials=None,scale=1):
    validate_mesh(mesh)
    if not math.isfinite(scale) or not 0<scale<=100000:raise ValueError("invalid scale")
    materials=materials or {};groups={}
    for tri,mat in mesh.faces:groups.setdefault(mat,[]).append(tri)
    if set(materials)-set(groups) or len(groups)>256:raise ValueError("invalid materials")
    lines=[f"CHIMSTER_MESH_1 {len(groups)}"]
    for mat,faces in sorted(groups.items()):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}",mat):raise ValueError("invalid material ID")
        spec=materials.get(mat,{});diff=texture_path(spec.get("diffuse",""));normal=texture_path(spec.get("normal",""))
        cut=spec.get("cutout",False)
        if not isinstance(cut,bool):raise ValueError("cutout must be boolean")
        ids=sorted({i for f in faces for i in f})
        if len(ids)>65535 or len(faces)>65535:raise ValueError("split shapes to 16-bit budgets")
        mapping={j:i for i,j in enumerate(ids)};verts=[mesh.vertices[j] for j in ids];normals=[[0.,0.,0.] for j in ids]
        tris=[tuple(mapping[j] for j in f) for f in faces]
        for a,b,c in tris:
            n=cross(tuple(verts[b][i]-verts[a][i] for i in range(3)),tuple(verts[c][i]-verts[a][i] for i in range(3)))
            for j in (a,b,c):
                for i in range(3):normals[j][i]+=n[i]
        # std::quoted uses C++ backslash escaping; JSON ASCII strings suffice for these safe paths.
        lines.append(f'{json.dumps(mat)} {json.dumps(diff)} {json.dumps(normal)} {int(cut)} {len(ids)} {len(tris)}')
        for i,j in enumerate(ids):
            v=verts[i];u,w=mesh.uv[j];n=normals[i];length=math.sqrt(sum(x*x for x in n));n=[x/length for x in n] if length else [0,0,1]
            values=[*(x*scale for x in v),u,1-w,*n]
            if any(not math.isfinite(x) or abs(x)>1e9 for x in values):raise ValueError("vertex exceeds bounds")
            lines.append(" ".join(format(x,".9g") for x in values))
        lines.extend(" ".join(map(str,t)) for t in tris)
    return "\n".join(lines)+"\n"

def export(mesh,game,output,helper,materials=None,scale=1,box_collision=False):
    if box_collision and game not in {'newvegas','fallout3'}:raise ValueError('box collision is experimental FO3/FNV only')
    if game not in GAMES:raise ValueError("unsupported modern NIF game")
    p=Path(output)
    if p.suffix.lower()!=".nif" or p.exists() or p.is_symlink():raise ValueError("expected new NIF")
    helper=Path(helper).resolve(strict=True)
    if not helper.is_file() or helper.suffix.lower() in {".bat",".cmd",".ps1"}:raise ValueError("expected native helper executable")
    data=mesh_exchange(mesh,materials,scale)
    with tempfile.TemporaryDirectory() as d:
        source=Path(d)/"mesh.cmesh";dest=Path(d)/"output.nif"
        source.write_text(data,encoding="ascii")
        cp=subprocess.run([str(helper),game,str(source),str(dest)]+(["box"] if box_collision else []),shell=False,capture_output=True,text=True,timeout=180)
        if cp.returncode:raise RuntimeError(cp.stderr[-4000:])
        report=json.loads(cp.stdout)
        if (box_collision and not report.get("box_collision")) or report["triangles"]!=len(mesh.faces) or not dest.is_file() or not dest.read_bytes().startswith(b"Gamebryo File Format"):raise ValueError("native helper output mismatch")
        with p.open("xb") as f:
            with dest.open("rb") as src:shutil.copyfileobj(src,f)
    return {**report,"output":str(p),"status":"native Nifly roundtrip; game runtime not verified"}
