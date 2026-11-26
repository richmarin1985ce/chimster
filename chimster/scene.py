"""MIT portable scene model: local coordinates, immutable transforms, undoable edits.
Not a Bethesda plugin or native engine scene graph."""
from dataclasses import dataclass,replace,asdict
from pathlib import Path
from math import cos,sin,radians,isfinite,sqrt
import json
from .flora import Mesh,Recipe,generate,cross
from .lod import terrain_grid,validate_mesh

@dataclass(frozen=True)
class Instance:
    id:str
    asset:str
    x:float=0
    y:float=0
    z:float=0
    yaw:float=0
    scale:float=1
    def validate(self):
        if not self.id or not self.asset or not all(isfinite(v) and abs(v)<=1e7 for v in (self.x,self.y,self.z,self.yaw,self.scale)) or self.scale<=0:raise ValueError("invalid transform")

class Scene:
    def __init__(self,assets=None,instances=()):
        self.assets=dict(assets or {})
        for m in self.assets.values():validate_mesh(m)
        self.instances=tuple(instances);self._undo=[];self._redo=[];self.validate(self.instances)
    def validate(self,items):
        if len(items)>5000 or len({i.id for i in items})!=len(items):raise ValueError("duplicate or excessive instances")
        for i in items:
            i.validate()
            if i.asset not in self.assets:raise ValueError("unknown asset")
    def change(self,items):
        items=tuple(items);self.validate(items)
        self._undo.append(self.instances);self._undo=self._undo[-100:];self._redo.clear();self.instances=items
    def add(self,instance):self.change((*self.instances,instance))
    def update(self,id,**changes):
        if not any(i.id==id for i in self.instances):raise ValueError("unknown instance")
        self.change(replace(i,**changes) if i.id==id else i for i in self.instances)
    def remove(self,id):
        if not any(i.id==id for i in self.instances):raise ValueError("unknown instance")
        self.change(i for i in self.instances if i.id!=id)
    def undo(self):
        if self._undo:self._redo.append(self.instances);self.instances=self._undo.pop()
    def redo(self):
        if self._redo:self._undo.append(self.instances);self.instances=self._redo.pop()
    def save(self,path):
        assets={k:{"vertices":m.vertices,"uv":m.uv,"faces":m.faces} for k,m in self.assets.items()}
        with Path(path).open("x",encoding="utf-8") as f:json.dump({"version":1,"assets":assets,"instances":[asdict(i) for i in self.instances]},f,allow_nan=False)
    @classmethod
    def load(cls,path):
        p=Path(path)
        if p.stat().st_size>64*1024*1024:raise ValueError("scene file too large")
        data=json.loads(p.read_text(encoding="utf-8"))
        if data["version"]!=1:raise ValueError("unsupported scene version")
        assets={k:Mesh([tuple(v) for v in m["vertices"]],[tuple(v) for v in m["uv"]],[(tuple(t),mat) for t,mat in m["faces"]]) for k,m in data["assets"].items()}
        return cls(assets,[Instance(**i) for i in data["instances"]])

def transformed(mesh,i):
    a=radians(i.yaw);c,s=cos(a),sin(a)
    return [(i.x+i.scale*(c*x-s*y),i.y+i.scale*(s*x+c*y),i.z+i.scale*z) for x,y,z in mesh.vertices]

def load_obj(path):
    """Read Chimster-style triangulated OBJ with v/vt faces; no external MTL reads."""
    p=Path(path)
    if p.stat().st_size>64*1024*1024:raise ValueError("OBJ too large")
    verts=[];uv=[];m=Mesh();lookup={};mat="default"
    with p.open(encoding="utf-8") as f:
        for line in f:
            q=line.split()
            if not q or q[0].startswith("#"):continue
            if q[0]=="v" and len(q)>=4:verts.append(tuple(map(float,q[1:4])))
            elif q[0]=="vt" and len(q)>=3:uv.append(tuple(map(float,q[1:3])))
            elif q[0]=="usemtl":mat=" ".join(q[1:])
            elif q[0]=="f":
                if len(q)!=4:raise ValueError("triangulated OBJ required")
                t=[]
                for token in q[1:]:
                    fields=token.split("/");vi=int(fields[0]);ti=int(fields[1]) if len(fields)>1 and fields[1] else 0
                    if not 1<=vi<=len(verts) or ti<0 or ti>len(uv):raise ValueError("positive OBJ indices required")
                    key=(vi,ti)
                    if key not in lookup:
                        lookup[key]=len(m.vertices);m.vertices.append(verts[vi-1]);m.uv.append(uv[ti-1] if ti else (0,0))
                    t.append(lookup[key])
                m.faces.append((tuple(t),mat))
            if len(verts)>300000 or len(uv)>300000 or len(m.faces)>300000:raise ValueError("OBJ exceeds viewport import limit")
    validate_mesh(m);return m

def demo_scene():
    h=[[.6*cos(x*.3)*sin(y*.3) for x in range(17)] for y in range(17)]
    assets={"terrain":terrain_grid(h,spacing=2,origin=(-16,-16)),"tree":generate(Recipe(),2),"shrub":generate(Recipe(species="shrub",height=1.2,radius=.05,branches=8,leaves=32),1)}
    objects=[Instance("ground","terrain")]
    for i,(x,y) in enumerate([(-8,-6),(1,3),(8,-3),(-3,10)]):objects.append(Instance(f"tree-{i}","tree",x,y,0,i*60,.75+i*.1))
    return Scene(assets,objects)

@dataclass(frozen=True)
class Camera:
    yaw:float=35
    pitch:float=32
    zoom:float=12
    center:tuple=(0,0,0)

def project(p,camera,w,h):
    x,y,z=(p[i]-camera.center[i] for i in range(3))
    a,b=radians(camera.yaw),radians(camera.pitch)
    right=cos(a)*x-sin(a)*y;forward=sin(a)*x+cos(a)*y
    up=cos(b)*z-sin(b)*forward;depth=sin(b)*z+cos(b)*forward
    return w/2+right*camera.zoom,h/2-up*camera.zoom,depth

def frame(scene,camera,w,h,budget=16000):
    """Painter-sorted shaded polygons, bounded triangle count.
    Approximate depth ordering, no texture mapping, not a game renderer."""
    result=[];total=sum(len(scene.assets[i.asset].faces) for i in scene.instances)
    step=max(1,(total+budget-1)//budget)
    for i in scene.instances:
        m=scene.assets[i.asset];v=transformed(m,i);p=[project(x,camera,w,h) for x in v]
        for tri,mat in m.faces[::step]:
            coords=[p[j] for j in tri]
            a,b,c=[v[j] for j in tri]
            normal=cross(tuple(b[k]-a[k] for k in range(3)),tuple(c[k]-a[k] for k in range(3)));length=sqrt(sum(x*x for x in normal))
            shade=.55+.45*abs((normal[0]*.3+normal[1]*.4+normal[2]*.866)/length) if length else .55
            rgb=(77,115,66) if "leaf" in mat or "terrain" in mat else (116,88,58) if "bark" in mat else (150,155,165)
            color="#"+"".join(f"{min(255,round(x*shade)):02x}" for x in rgb)
            result.append((sum(q[2] for q in coords)/3,i.id,tuple(k for q in coords for k in q[:2]),color))
    result.sort(key=lambda r:r[0]);return result
