"""Transactional portable interior project editing; native payloads remain explicit."""
from copy import deepcopy
from .interior_layout import validate,point,bounds
from .fnv_content import ident

def cell(project,cell_id):
    matches=[c for c in project["cells"] if c["id"]==cell_id]
    if len(matches)!=1:raise ValueError("unknown or duplicate cell")
    return matches[0]

def check(project):
    if project.get("schema")!=1 or not project.get("cells"):raise ValueError("expected interior project")
    ids=set()
    for c in project["cells"]:
        ident(c["id"])
        if c["id"].casefold() in ids:raise ValueError("duplicate cell")
        ids.add(c["id"].casefold())
        layout=c.get("layout",{"schema":1,"rooms":[]})
        report=validate(layout)
        if not report["valid"]:raise ValueError("; ".join(report["issues"]))
        places={}
        for p in c.get("placements",[]):
            ident(p["id"]);point(p["position"])
            if p["id"].casefold() in places:raise ValueError("duplicate placement")
            places[p["id"].casefold()]=p
        portals={p["id"]:p for p in layout.get("portals",[])}
        for pid,rid in c.get("portal_doors",{}).items():
            if pid not in portals or rid.casefold() not in places:raise ValueError("missing portal or door")
            pos=places[rid.casefold()]["position"]
            corners=portals[pid]["corners"]
            if any(not min(q[i] for q in corners)-1e-5<=pos[i]<=max(q[i] for q in corners)+1e-5 for i in range(3)):
                raise ValueError("bound door must lie on portal rectangle")
    return project

def make_portal(layout,id,a,b,inset=0.1):
    ident(id)
    if not 0<=inset<.5:raise ValueError("invalid portal inset")
    rooms={r["id"]:bounds(r) for r in layout["rooms"]}
    if a==b or a not in rooms or b not in rooms:raise ValueError("select two rooms")
    lo1,hi1=rooms[a];lo2,hi2=rooms[b]
    faces=[]
    for axis in range(3):
        if abs(hi1[axis]-lo2[axis])<=1e-6:faces.append((axis,hi1[axis]))
        elif abs(hi2[axis]-lo1[axis])<=1e-6:faces.append((axis,hi2[axis]))
    if len(faces)!=1:raise ValueError("rooms need one shared face")
    axis,v=faces[0];u,w=[i for i in range(3) if i!=axis]
    limits=[]
    for i in (u,w):
        low=max(lo1[i],lo2[i]);high=min(hi1[i],hi2[i])
        if high-low<=1e-6:raise ValueError("rooms do not share an area")
        d=(high-low)*inset;limits.append((low+d,high-d))
    corners=[]
    for x,y in ((0,0),(1,0),(1,1),(0,1)):
        p=[0.,0.,0.];p[axis]=v;p[u]=limits[0][x];p[w]=limits[1][y];corners.append(p)
    return {"id":id,"rooms":[a,b],"corners":corners}

class History:
    def __init__(self,project):
        self.current=deepcopy(check(project));self.past=[];self.future=[]
    def commit(self,project):
        candidate=deepcopy(check(project))
        if candidate==self.current:return
        self.past.append(self.current);self.past=self.past[-30:]
        self.current=candidate;self.future.clear()
    def undo(self):
        if self.past:self.future.append(self.current);self.current=self.past.pop()
    def redo(self):
        if self.future:self.past.append(self.current);self.current=self.future.pop()
    def edit(self,cell_id,kind,row):
        p=deepcopy(self.current);c=cell(p,cell_id)
        if kind=="placement":items=c.setdefault("placements",[])
        elif kind in ("room","portal","trigger","node"):
            items=c.setdefault("layout",{"schema":1,"rooms":[]}).setdefault(kind+"s",[])
        else:raise ValueError("unknown edit type")
        ident(row["id"])
        matches=[i for i,r in enumerate(items) if r["id"]==row["id"]]
        if matches:items[matches[0]]=deepcopy(row)
        else:items.append(deepcopy(row))
        self.commit(p)
    def bind(self,cell_id,portal_id,door_id):
        p=deepcopy(self.current);c=cell(p,cell_id)
        c.setdefault("portal_doors",{})[portal_id]=door_id
        self.commit(p)
