"""Shared Asset Forge editing session. Intermediate geometry, explicit native export."""
from copy import deepcopy
from math import cos, sin, radians, isfinite
import re
from .flora import Mesh, write_obj
from .lod import validate_mesh, bounds
from .modern_nif import texture_path

def checked(mesh):
    validate_mesh(mesh)
    if max(len(mesh.vertices),len(mesh.faces))>300000:
        raise ValueError("Asset Forge geometry limit exceeded")
    if any(not isinstance(m,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}",m) for _,m in mesh.faces):
        raise ValueError("Material IDs must be 1–100 ASCII letters, digits, underscores or hyphens")
    if any(abs(v)>1e8 for p in mesh.vertices+mesh.uv for v in p):
        raise ValueError("Geometry exceeds coordinate limit")
    return mesh

class Session:
    def __init__(self,mesh):
        self.mesh=deepcopy(checked(mesh))
        self.materials={}
        self.past=[];self.future=[]
        self.collision=None;self.collision_stale=False
    def groups(self):
        return sorted({m for _,m in self.mesh.faces})
    def commit(self,mesh,materials,*,collision_update=False,collision=None):
        checked(mesh)
        self.past.append((self.mesh,self.materials,self.collision,self.collision_stale))
        self.past=self.past[-5:];self.future.clear()
        if collision_update:
            self.collision=deepcopy(collision);self.collision_stale=False
        elif self.collision is not None and (mesh.vertices!=self.mesh.vertices or [t for t,_ in mesh.faces]!=[t for t,_ in self.mesh.faces]):
            self.collision_stale=True
        self.mesh,self.materials=mesh,materials
    def undo(self):
        if self.past:
            self.future.append((self.mesh,self.materials,self.collision,self.collision_stale))
            self.mesh,self.materials,self.collision,self.collision_stale=self.past.pop()
    def redo(self):
        if self.future:
            self.past.append((self.mesh,self.materials,self.collision,self.collision_stale))
            self.mesh,self.materials,self.collision,self.collision_stale=self.future.pop()
    def transform(self,scale=1,yaw=0,ground=False):
        if not all(isfinite(v) for v in (scale,yaw)) or not 0<scale<=100000:
            raise ValueError("Invalid transform")
        a=radians(yaw%360);c,s=cos(a),sin(a)
        bottom=bounds(self.mesh)[2][0] if ground else 0
        mesh=Mesh([(scale*(c*x-s*y),scale*(s*x+c*y),scale*(z-bottom))
                   for x,y,z in self.mesh.vertices],list(self.mesh.uv),list(self.mesh.faces))
        self.commit(mesh,deepcopy(self.materials))
    def bind(self,group,diffuse="",normal="",cutout=False):
        if group not in self.groups() or type(cutout) is not bool:
            raise ValueError("Unknown material or invalid alpha mode")
        materials=deepcopy(self.materials)
        materials[group]={"diffuse":texture_path(diffuse),"normal":texture_path(normal),"cutout":cutout}
        self.commit(self.mesh,materials)
    def simplify(self,cell):
        from .lod_assets import simplify
        mesh=simplify(self.mesh,cell)
        if set(m for _,m in mesh.faces)!=set(self.groups()):
            raise ValueError("Simplification would remove a material group")
        self.commit(mesh,deepcopy(self.materials))
    def edges(self):
        return sorted({tuple(sorted((t[i],t[(i+1)%3]))) for t,_ in self.mesh.faces for i in range(3)})
    def selection_vertices(self,mode,indices):
        ids=set(indices)
        if not ids or any(type(i) is not int or i<0 for i in ids):raise ValueError("Select valid indices")
        if mode=="vertex":
            if max(ids)>=len(self.mesh.vertices):raise ValueError("Vertex index out of range")
            return ids
        items=self.edges() if mode=="edge" else [t for t,_ in self.mesh.faces] if mode=="face" else None
        if items is None or max(ids)>=len(items):raise ValueError("Selection out of range")
        return {v for i in ids for v in items[i]}
    def move_selection(self,mode,indices,delta):
        if len(delta)!=3 or not all(isfinite(x) for x in delta):raise ValueError("Invalid movement")
        ids=self.selection_vertices(mode,indices);m=deepcopy(self.mesh)
        for i in ids:m.vertices[i]=tuple(x+y for x,y in zip(m.vertices[i],delta))
        from .flora import cross
        for t,_ in m.faces:
            if ids.intersection(t):
                a,b,c=[m.vertices[i] for i in t]
                n=cross(tuple(y-x for x,y in zip(a,b)),tuple(y-x for x,y in zip(a,c)))
                if not any(n):raise ValueError("Movement collapses a triangle")
        self.commit(m,deepcopy(self.materials))
    def split_edge(self,index):
        a,b=self.edges()[index] if type(index) is int and 0<=index<len(self.edges()) else (None,None)
        if a is None:raise ValueError("Invalid edge")
        m=deepcopy(self.mesh);mid=len(m.vertices)
        m.vertices.append(tuple((x+y)/2 for x,y in zip(m.vertices[a],m.vertices[b])))
        m.uv.append(tuple((x+y)/2 for x,y in zip(m.uv[a],m.uv[b])))
        faces=[]
        for t,mat in m.faces:
            if a in t and b in t:
                for i in range(3):
                    x,y,z=t[i],t[(i+1)%3],t[(i+2)%3]
                    if {x,y}=={a,b}:
                        faces.extend([((x,mid,z),mat),((mid,y,z),mat)]);break
            else:faces.append((t,mat))
        m.faces=faces;self.commit(m,deepcopy(self.materials))
    def delete_faces(self,indices):
        ids=set(indices);self.selection_vertices("face",ids)
        m=deepcopy(self.mesh);m.faces=[f for i,f in enumerate(m.faces) if i not in ids]
        used=sorted({v for t,_ in m.faces for v in t});remap={v:i for i,v in enumerate(used)}
        m=Mesh([m.vertices[i] for i in used],[m.uv[i] for i in used],
               [(tuple(remap[v] for v in t),mat) for t,mat in m.faces])
        self.commit(m,{k:v for k,v in self.materials.items() if k in {mat for _,mat in m.faces}})
    def assign_faces(self,indices,group):
        ids=set(indices);self.selection_vertices("face",ids)
        if group not in self.groups():raise ValueError("Unknown material group")
        m=deepcopy(self.mesh);m.faces=[(t,group if i in ids else mat) for i,(t,mat) in enumerate(m.faces)]
        self.commit(m,{k:v for k,v in self.materials.items() if k in {mat for _,mat in m.faces}})
    def extrude_faces(self,indices,delta):
        from .asset_topology import extrude
        ids=set(indices);self.selection_vertices("face",ids)
        mesh,new_faces=extrude(self.mesh,ids,delta)
        self.commit(mesh,deepcopy(self.materials))
        return new_faces
    def weld_vertices(self,indices,tolerance):
        from .asset_topology import weld
        ids=self.selection_vertices("vertex",indices)
        mesh=weld(self.mesh,ids,tolerance)
        self.commit(mesh,{k:v for k,v in self.materials.items() if k in {mat for _,mat in mesh.faces}})
    def project_uv(self,indices,plane):
        from .asset_topology import planar_uv
        ids=set(indices);self.selection_vertices("face",ids)
        self.commit(planar_uv(self.mesh,ids,plane),deepcopy(self.materials))
    def transform_uv(self,mode,indices,scale,offset):
        ids=self.selection_vertices(mode,indices)
        if len(scale)!=2 or len(offset)!=2 or not all(isfinite(v) for v in (*scale,*offset)) or 0 in scale:
            raise ValueError("Invalid UV transform")
        m=deepcopy(self.mesh)
        for i in ids:m.uv[i]=tuple(m.uv[i][k]*scale[k]+offset[k] for k in range(2))
        self.commit(m,deepcopy(self.materials))
    def gizmo(self,mode,indices,operation,axis,amount):
        from .asset_gizmo import transformed
        ids=self.selection_vertices(mode,indices)
        self.commit(transformed(self.mesh,ids,operation,axis,amount),deepcopy(self.materials))
    def set_collision(self,recipe):
        from .collision_materials import validate
        if recipe is not None:validate(recipe,"newvegas")
        self.commit(self.mesh,self.materials,collision_update=True,collision=recipe)
    def add_collision_box(self,mode,indices,name,material="stone",padding=.01):
        if not isfinite(padding) or padding<0:raise ValueError("Invalid padding")
        ids=self.selection_vertices(mode,indices)
        points=[self.mesh.vertices[i] for i in ids]
        lo=[min(p[k] for p in points)-padding for k in range(3)]
        hi=[max(p[k] for p in points)+padding for k in range(3)]
        recipe=deepcopy(self.collision) if self.collision else {"kind":"compound_aabb","list_material":"stone","boxes":[]}
        if self.collision_stale:raise ValueError("Review existing collision before adding a box")
        recipe["boxes"].append({"id":name,"min":lo,"max":hi,"material":material})
        self.set_collision(recipe)
    def report(self):
        return {**self.mesh.stats(),"bounds":bounds(self.mesh),"materials":self.groups(),
                "bindings":deepcopy(self.materials)}
    def export_obj(self,path):
        write_obj(self.mesh,path)
    def export_nif(self,path,game,scale,helper=None,box_collision=False,compound=False):
        if compound and (self.collision is None or self.collision_stale or box_collision):
            raise ValueError("Review compound collision before export; choose one collision mode")
        if compound and game not in ("fallout3","newvegas"):raise ValueError("Compound collision is FO3/FNV only")
        if game in ("morrowind","openmw"):
            if box_collision or any(v["normal"] for v in self.materials.values()):
                raise ValueError("Legacy exporter does not support these options")
            # Legacy alpha test is determined by the material suffix.
            if any(v["cutout"] != k.endswith("__cutout") or
                   (v["cutout"] and not v["diffuse"]) for k,v in self.materials.items()):
                raise ValueError("Legacy alpha requires a textured __cutout material")
            from .nif_export import export_legacy
            return export_legacy(self.mesh,path,game,scale,
                                 {k:v["diffuse"] for k,v in self.materials.items() if v["diffuse"]})
        if not helper:
            raise ValueError("Select a trusted native NIF helper")
        from .modern_nif import export
        materials={k:{"cutout":k.endswith("__cutout"),**self.materials.get(k,{})} for k in self.groups()}
        if compound:return export(self.mesh,game,path,helper,materials,scale,compound_collision=self.collision)
        return export(self.mesh,game,path,helper,materials,scale,box_collision)
