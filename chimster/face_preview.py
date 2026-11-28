"""Local OBJ blendshape preview, independent of proprietary game assets."""
from pathlib import Path
import json,math
from .phoneme_synthesis import frames

MAX_VERTICES=12000
MAX_TRIANGLES=20000

def obj(path):
    path=Path(path)
    if path.stat().st_size>16*1024*1024:raise ValueError("OBJ exceeds preview limit")
    vertices=[];triangles=[]
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            p=line.split("#",1)[0].split()
            if not p:continue
            if p[0]=="v":
                if len(p)!=4:raise ValueError("expected XYZ vertex")
                xyz=tuple(map(float,p[1:]))
                if not all(math.isfinite(x) and abs(x)<=1e6 for x in xyz):raise ValueError("invalid vertex")
                vertices.append(xyz)
                if len(vertices)>MAX_VERTICES:raise ValueError("too many vertices")
            elif p[0]=="f":
                if len(p)<4 or len(p)>65:raise ValueError("unsupported face")
                ids=[]
                for token in p[1:]:
                    i=int(token.split("/")[0])
                    if not i:raise ValueError("invalid OBJ index")
                    i=i-1 if i>0 else len(vertices)+i
                    if not 0<=i<len(vertices):raise ValueError("invalid vertex reference")
                    ids.append(i)
                for j in range(1,len(ids)-1):triangles.append((ids[0],ids[j],ids[j+1]))
                if len(triangles)>MAX_TRIANGLES:raise ValueError("too many triangles")
    if not vertices or not triangles:raise ValueError("mesh must contain vertices and faces")
    return vertices,triangles

class Rig:
    def __init__(self,base,triangles,targets):
        self.base=base;self.triangles=triangles;self.targets=targets
    def pose(self,weights):
        unknown={s for s,w in weights.items() if w and s not in self.targets}
        if unknown:raise ValueError("model missing active slots: "+str(sorted(unknown)))
        result=[list(v) for v in self.base]
        for s,w in weights.items():
            if not math.isfinite(w) or not 0<=w<=1:raise ValueError("invalid morph weight")
            if not w:continue
            for i,delta in enumerate(self.targets[s]):
                for j in range(3):result[i][j]+=delta[j]*w
        return result

def load(path):
    path=Path(path).resolve(strict=True)
    if path.stat().st_size>1024*1024:raise ValueError("rig manifest too large")
    data=json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema")!=1 or not isinstance(data.get("targets"),dict):raise ValueError("invalid rig manifest")
    def local(name):
        p=path.parent/name
        if p.is_symlink() or not p.resolve().is_relative_to(path.parent) or p.suffix.lower()!=".obj":
            raise ValueError("rig assets must be local OBJ files")
        return p
    base,tri=obj(local(data["base"]));targets={}
    for s,name in data["targets"].items():
        slot=int(s)
        if str(slot)!=s or not 0<=slot<33:raise ValueError("invalid Skyrim raw slot")
        v,t=obj(local(name))
        if t!=tri or len(v)!=len(base):raise ValueError("morph OBJ topology must match base exactly")
        targets[slot]=[tuple(a-b for a,b in zip(x,y)) for x,y in zip(v,base)]
    if not targets:raise ValueError("at least one morph target required")
    return Rig(base,tri,targets)

def animation(rig,rows,duration,profile):
    grid,slots=frames(rows,duration,profile)
    if set(slots)-rig.targets.keys():raise ValueError("rig does not contain every active facial slot")
    return grid

def project(vertices,triangles,width,height,yaw=0,pitch=0,zoom=1,bounds=None):
    """Orthographic shaded triangle projection; no GPU dependency."""
    if bounds is None:
        lo=[min(v[j] for v in vertices) for j in range(3)]
        hi=[max(v[j] for v in vertices) for j in range(3)]
        center=[(a+b)/2 for a,b in zip(lo,hi)]
        radius=max(b-a for a,b in zip(lo,hi)) or 1
    else:center,radius=bounds
    scale=min(width,height)*.78/radius*zoom
    cy,sy=math.cos(yaw),math.sin(yaw);cp,sp=math.cos(pitch),math.sin(pitch)
    pts=[]
    for v in vertices:
        x,y,z=[v[j]-center[j] for j in range(3)]
        x,z=x*cy+z*sy,-x*sy+z*cy
        y,z=y*cp-z*sp,y*sp+z*cp
        pts.append((x,y,z))
    faces=[]
    for a,b,c in triangles:
        v=[pts[i] for i in (a,b,c)]
        u=[v[1][j]-v[0][j] for j in range(3)];w=[v[2][j]-v[0][j] for j in range(3)]
        normal=(u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0])
        mag=math.sqrt(sum(x*x for x in normal))
        if not mag:continue
        shade=int(85+135*abs(normal[2]/mag))
        points=[n for x,y,z in v for n in (width/2+x*scale,height/2-y*scale)]
        faces.append((sum(x[2] for x in v)/3,points,f"#{shade:02x}{int(shade*.86):02x}{int(shade*.78):02x}"))
    return sorted(faces,key=lambda f:f[0])
