"""Bounded native static mesh import. Does not preserve the original NIF graph."""
from pathlib import Path
import shlex
import subprocess
from .flora import Mesh
from .asset_forge import Session
from .modern_nif import texture_path

def parse_exchange(data):
    if len(data)>64*1024*1024:raise ValueError("Mesh exchange exceeds limit")
    lines=iter(data.splitlines())
    def line():
        try:return next(lines)
        except StopIteration:raise ValueError("Truncated mesh exchange") from None
    header=line().split()
    if len(header)!=2 or header[0]!="CHIMSTER_IMPORT_1":raise ValueError("Unknown mesh exchange")
    count=int(header[1])
    if not 1<=count<=256:raise ValueError("Shape count limit")
    mesh=Mesh();materials={}
    for _ in range(count):
        name,diffuse,normal,cut,nv,nt=shlex.split(line())
        nv,nt=int(nv),int(nt)
        if name in materials or cut not in ("0","1") or not (1<=nv<=65535 and 1<=nt<=65535):
            raise ValueError("Invalid shape header")
        if len(mesh.vertices)+nv>300000 or len(mesh.faces)+nt>300000:raise ValueError("Geometry limit")
        verts=[];uv=[];faces=[]
        for _ in range(nv):
            x,y,z,u,v=map(float,line().split());verts.append((x,y,z));uv.append((u,v))
        for _ in range(nt):
            t=tuple(map(int,line().split()))
            if len(t)!=3 or any(i<0 or i>=nv for i in t):raise ValueError("Local triangle index out of range")
            faces.append(t)
        mesh.add(verts,uv,faces,name)
        materials[name]={"diffuse":texture_path(diffuse),"normal":texture_path(normal),"cutout":cut=="1"}
    if any(l.strip() for l in lines):raise ValueError("Trailing mesh data")
    s=Session(mesh);s.materials=materials
    return s

def import_modern(path,helper):
    p=Path(path).resolve(strict=True);h=Path(helper).resolve(strict=True)
    if p.suffix.lower()!=".nif" or not p.is_file() or p.stat().st_size>128*1024*1024:
        raise ValueError("Expected bounded NIF file")
    if not h.is_file() or h.suffix.lower() in {".bat",".cmd",".ps1"}:raise ValueError("Expected trusted native helper executable")
    try:
        cp=subprocess.run([str(h),"extract-mesh",str(p)],capture_output=True,text=True,encoding="ascii",timeout=180,check=False)
    except subprocess.TimeoutExpired as e:raise RuntimeError("Native mesh import timed out") from e
    if cp.returncode:raise RuntimeError(cp.stderr[-4000:])
    return parse_exchange(cp.stdout)
