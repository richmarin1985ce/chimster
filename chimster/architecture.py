"""Original modular building geometry. Meter units; separate solid collision pieces."""
from dataclasses import dataclass,asdict
from math import isfinite
from pathlib import Path
import json
from .flora import Mesh,write_obj
from .lod import validate_mesh
@dataclass(frozen=True)
class Building:
    width:float=8
    depth:float=6
    height:float=3
    wall:float=.25
    doorway:float=1.2
    door_height:float=2.1
    def validate(self):
        if not all(isfinite(x) and 0<x<=100 for x in vars(self).values()):raise ValueError("invalid dimensions")
        if 2*self.wall>=min(self.width,self.depth) or self.doorway>=self.width-2*self.wall or self.door_height>=self.height:raise ValueError("invalid wall or doorway")
        return self
def pieces(b):
    b.validate();w,d,h,t=b.width,b.depth,b.height,b.wall
    a=(w-b.doorway)/2;c=a+b.doorway
    return [("floor",(0,0,-t),(w,d,0)),("roof",(0,0,h),(w,d,h+t)),
      ("west",(0,0,0),(t,d,h)),("east",(w-t,0,0),(w,d,h)),
      ("north",(t,d-t,0),(w-t,d,h)),("south_left",(t,0,0),(a,t,h)),
      ("south_right",(c,0,0),(w-t,t,h)),("lintel",(a,0,b.door_height),(c,t,h))]
def box_mesh(lo,hi,mat):
    x,y,z=lo;a,b,c=hi
    v=[(x,y,z),(a,y,z),(a,b,z),(x,b,z),(x,y,c),(a,y,c),(a,b,c),(x,b,c)]
    # Separate vertices by face for hard normals and per-face UVs.
    m=Mesh()
    for face in ((3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
        i=len(m.vertices);m.vertices.extend(v[j] for j in face);m.uv.extend([(0,0),(1,0),(1,1),(0,1)])
        m.faces.extend([((i,i+1,i+2),mat),((i,i+2,i+3),mat)])
    return m
def generate(b):
    m=Mesh();bounds=[]
    for name,lo,hi in pieces(b):
        part=box_mesh(lo,hi,"floor" if name=="floor" else "roof" if name=="roof" else "wall")
        i=len(m.vertices);m.vertices.extend(part.vertices);m.uv.extend(part.uv);m.faces.extend((tuple(i+j for j in t),mat) for t,mat in part.faces)
        bounds.append({"id":name,"min":lo,"max":hi,"material":"wood" if name=="floor" else "sheet_metal" if name=="roof" else "stone"})
    validate_mesh(m);return m,bounds
def export(b,folder):
    m,boxes=generate(b);p=Path(folder);p.mkdir(parents=True,exist_ok=False)
    write_obj(m,p/"building.obj")
    (p/"collision.json").write_text(json.dumps({"kind":"compound_aabb","boxes":boxes},indent=2),encoding="utf-8")
    result={"recipe":asdict(b),"triangles":len(m.faces),"collision_pieces":len(boxes),"status":"portable modular geometry and collision recipe; native game conversion pending"}
    (p/"manifest.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
