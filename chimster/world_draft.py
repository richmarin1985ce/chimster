"""Reviewable cell-edit drafts, never a native plugin writer."""
from copy import deepcopy
from math import isfinite, floor
from pathlib import Path
import json
import re
from .record_graph import Identity
from .world_browser import Browser, label


def editor_id(value):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}",value):
        raise ValueError("Expected ASCII editor ID (1–64 characters)")
    return value


def key_json(key):
    return None if key is None else [key.origin,key.local]


class Draft:
    def __init__(self, browser, name="ChimsterDraft.esp"):
        if browser.profile!="new-vegas":
            raise ValueError("Native world drafts are New Vegas only")
        self.original = browser
        self.name = name.lower()
        if not re.fullmatch(r"[a-z0-9_-]+\.esp",self.name) or any(k.origin==self.name or r["plugin"]==self.name for k,r in browser.winners.items()) or any(p.name.casefold()==self.name for p in getattr(browser,"source_paths",())):
            raise ValueError("Draft identity collides with source")
        self.rows = {}
        self.operations = []
        self.undo_stack = []
        self.redo_stack = []
        self.cursor = 0x800

    def checkpoint(self):
        self.undo_stack.append((deepcopy(self.rows),deepcopy(self.operations),self.cursor))
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append((deepcopy(self.rows),deepcopy(self.operations),self.cursor))
            self.rows,self.operations,self.cursor=self.undo_stack.pop()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append((deepcopy(self.rows),deepcopy(self.operations),self.cursor))
            self.rows,self.operations,self.cursor=self.redo_stack.pop()

    def index(self):
        # Build from winners then add draft rows. Preserve original provider history.
        result=Browser([("snapshot.esp",(),list(self.original.winners.values())),(self.name,(),list(self.rows.values()))])
        for key, history in self.original.history.items():
            result.history[key]=list(history)+([self.name] if key in self.rows else [])
        return result

    def allocate(self):
        key=Identity(self.name,self.cursor)
        self.cursor+=1
        return key

    def unique_name(self, value, exclude=None):
        value=editor_id(value)
        if any(r["key"]!=exclude and r.get("editor_id","").casefold()==value.casefold()
               for r in self.index().active.values()):
            raise ValueError("Editor ID already exists")
        return value

    def create(self, name, world=None, grid=None):
        name=self.unique_name(name)
        index=self.index()
        if world is None:
            if grid is not None:raise ValueError("Interior must not have a grid")
        elif world not in index.worlds or not isinstance(grid,tuple) or len(grid)!=2 or any(type(v)!=int or not -32768<=v<=32767 for v in grid):
            raise ValueError("Exterior needs a live world and valid grid")
        elif index.coordinates.get((world,grid)):
            raise ValueError("Cell coordinates already occupied")
        self.checkpoint()
        key=self.allocate()
        row={"key":key,"signature":"CELL","plugin":self.name,"flags":0,"world":world,
             "cell":None,"bucket":None,"editor_id":name,"name":"","interior":world is None}
        if grid is not None:row["grid"]=grid
        self.rows[key]=row
        self.operations.append({"action":"create_cell","key":key_json(key),"editor_id":name,"world":key_json(world),"grid":grid})
        return key

    def duplicate(self,source,name,grid=None,static_only=False):
        """Copy a cell shell and eligible temporary static references atomically.

        Full fidelity duplication is not implied: LAND, NAVM, persistent objects,
        links, cell metadata and other native payloads are not cloned.
        """
        index=self.index()
        row=index.active.get(source)
        if not row or row["signature"]!="CELL" or row.get("persistent_cell"):
            raise ValueError("Select a normal cell to duplicate")
        world=row["world"]
        if world is not None and ("grid" not in row or grid is None):
            raise ValueError("Choose a different exterior grid")
        refs=[]
        omitted=[]
        for child in index.children.get(source,()):
            base=index.active.get(child.get("base"))
            if (child["signature"]=="REFR" and child.get("bucket")==9
                and not child.get("persistent") and not child["flags"]
                and base and base["signature"]=="STAT"
                and "position" in child and "rotation" in child
                and all(abs(v)<=1e-6 for v in child["rotation"][:2])
                and (child["key"].origin==self.name or child.get("transform_only_layout"))):
                refs.append(child)
            else:omitted.append(label(child["key"]))
        if omitted and not static_only:
            raise ValueError("Unsupported children; explicitly choose static-only duplication")
        if len(refs)>5000:raise ValueError("Duplicate placement limit")
        snapshot=(deepcopy(self.rows),deepcopy(self.operations),self.cursor)
        undo=list(self.undo_stack);redo=list(self.redo_stack)
        try:
            key=self.create(name,world,grid)
            dx,dy=(0,0) if world is None else tuple((grid[i]-row["grid"][i])*4096 for i in range(2))
            for ref in refs:
                x,y,z=ref["position"]
                pos=(x+dx,y+dy,z);yaw=ref["rotation"][2];scale=ref.get("scale",1)
                if not all(isfinite(v) and abs(v)<=1e7 for v in (*pos,yaw,scale)) or not .01<=scale<=10:
                    raise ValueError("Invalid copied placement")
                if grid is not None and tuple(floor(v/4096) for v in pos[:2])!=grid:
                    raise ValueError("Copied placement falls outside destination")
                refkey=self.allocate()
                self.rows[refkey]={"key":refkey,"signature":"REFR","plugin":self.name,"flags":0,"world":world,"cell":key,"bucket":9,"editor_id":"","name":"","base":ref["base"],"position":pos,"rotation":(0,0,yaw),"scale":scale,"persistent":False}
                self.operations.append({"action":"place_static","key":key_json(refkey),"cell":key_json(key),"base":key_json(ref["base"]),"position":pos,"yaw_radians":yaw,"scale":scale})
            self.operations.append({"action":"duplicate_static_cell","source":key_json(source),
                                    "key":key_json(key),"copied":len(refs),"omitted":omitted})
        except Exception:
            self.rows,self.operations,self.cursor=snapshot
            self.undo_stack=undo;self.redo_stack=redo
            raise
        self.undo_stack=undo+[snapshot]
        self.redo_stack=[]
        return key,{"copied":len(refs),"omitted":omitted,"scope":"cell shell and static references only"}

    def create_world(self,name,title,origin=(0,0),size=(1,1),environment=None):
        """Create a bounded initial exterior grid and its single persistent owner."""
        name=self.unique_name(name)
        from .world_environment import normalize
        if not isinstance(title,str) or "\0" in title or len(title.encode("cp1252"))>255:
            raise ValueError("Invalid worldspace title")
        if len(origin)!=2 or len(size)!=2 or any(type(v)!=int for v in (*origin,*size)) or min(size)<1 or size[0]*size[1]>256:
            raise ValueError("Initial grid must contain 1–256 cells")
        if any(not -32768<=origin[i]<=origin[i]+size[i]-1<=32767 for i in range(2)):
            raise ValueError("Invalid grid bounds")
        index=self.index()
        settings=normalize({"heights":(14000,10500),"lod_height":(10500,),
                            "flags":(0x10,),"map_offset":(1,0,0),**(environment or {})},index)
        if any(settings.get(k) is None for k in settings):settings={k:v for k,v in settings.items() if v is not None}
        from .fnv_world import encode_height
        steps=round(settings["heights"][0]/8)
        height_raw=encode_height([[steps]*33 for _ in range(33)])
        self.checkpoint()
        world=self.allocate();persistent=self.allocate()
        common={"plugin":self.name,"cell":None,"bucket":None,"name":""}
        self.rows[world]={**common,"key":world,"signature":"WRLD","flags":0,"world":None,
                          "editor_id":name,"name":title,"environment":settings,
                          "bounds":(origin,(origin[0]+size[0]-1,origin[1]+size[1]-1))}
        self.rows[persistent]={**common,"key":persistent,"signature":"CELL","flags":0x400,
                               "world":world,"editor_id":"","persistent_cell":True,"interior":False}
        for y in range(origin[1],origin[1]+size[1]):
            for x in range(origin[0],origin[0]+size[0]):
                key=self.allocate()
                self.rows[key]={**common,"key":key,"signature":"CELL","flags":0,"world":world,
                                "editor_id":"","interior":False,"grid":(x,y)}
                land=self.allocate()
                self.rows[land]={**common,"key":land,"signature":"LAND","flags":0,"world":world,"cell":key,"bucket":9,"editor_id":"","height_raw":height_raw}
        self.operations.append({"action":"create_world","key":key_json(world),"editor_id":name,
                                "title":title,"origin":origin,"size":size,"environment":settings,"starter_land":True})
        return world

    def set_environment(self,key,values):
        from .world_environment import normalize
        index=self.index()
        row=index.worlds.get(key)
        if row is None:raise ValueError("Select a live worldspace")
        values=normalize(values,index)
        self.checkpoint()
        env=dict(row.get("environment",{}))
        changes=dict(row.get("environment_changes",{}))
        for name,value in values.items():
            if value is None:env.pop(name,None)
            else:env[name]=value
            changes[name]=value
        self.rows[key]={**row,"plugin":self.name,"environment":env,"environment_changes":changes}
        self.operations.append({"action":"world_environment","key":key_json(key),"values":values})

    def world_properties(self,key,name,title):
        row=self.index().worlds.get(key)
        if row is None:raise ValueError("Select a live worldspace")
        name=self.unique_name(name,key)
        if not isinstance(title,str) or "\0" in title or len(title.encode("cp1252"))>255:
            raise ValueError("Invalid worldspace display name")
        self.checkpoint()
        self.rows[key]={**row,"editor_id":name,"name":title,"plugin":self.name}
        self.operations.append({"action":"world_properties","key":key_json(key),"editor_id":name,"title":title})

    def rename(self,key,name):
        row=self.index().active.get(key)
        if row is None or row["signature"]!="CELL":raise ValueError("Select a live cell")
        name=self.unique_name(name,key)
        self.checkpoint()
        self.rows[key]={**row,"editor_id":name,"plugin":self.name}
        self.operations.append({"action":"rename_cell","key":key_json(key),"editor_id":name})

    def place(self,cell,base,position,yaw=0,scale=1):
        index=self.index()
        parent=index.active.get(cell)
        model=index.active.get(base)
        if parent is None or parent["signature"]!="CELL" or parent.get("persistent_cell"):
            raise ValueError("Select a normal live cell")
        if model is None or model["signature"]!="STAT":
            raise ValueError("Only static base objects are enabled for draft placement")
        if len(position)!=3 or not all(isfinite(v) and abs(v)<=1e7 for v in (*position,yaw,scale)) or not .01<=scale<=10:
            raise ValueError("Invalid placement transform")
        if "grid" in parent and tuple(floor(v/4096) for v in position[:2])!=parent["grid"]:
            raise ValueError("Placement is outside selected exterior cell")
        self.checkpoint()
        key=self.allocate()
        self.rows[key]={"key":key,"signature":"REFR","plugin":self.name,"flags":0,
            "world":parent["world"],"cell":cell,"bucket":9,"editor_id":"","name":"",
            "base":base,"position":tuple(position),"rotation":(0,0,yaw),"scale":scale,"persistent":False}
        self.operations.append({"action":"place_static","key":key_json(key),"cell":key_json(cell),
            "base":key_json(base),"position":position,"yaw_radians":yaw,"scale":scale})
        return key

    def transform(self,key,position,yaw=0,scale=1):
        index=self.index()
        row=index.active.get(key)
        base=index.active.get(row.get("base")) if row else None
        if not row or row["signature"]!="REFR" or row.get("persistent") or row.get("bucket")!=9 or not base or base["signature"]!="STAT" or "position" not in row:
            raise ValueError("Select a temporary static reference with a valid transform")
        if key.origin!=self.name and (not row.get("transform_only_layout") or row["flags"] or any(abs(v)>1e-6 for v in row.get("rotation",(0,0,0))[:2])):
            raise ValueError("Flagged or tilted source references are not supported")
        parent=index.active[row["cell"]]
        if len(position)!=3 or not all(isfinite(v) and abs(v)<=1e7 for v in (*position,yaw,scale)) or not .01<=scale<=10:
            raise ValueError("Invalid placement transform")
        if "grid" in parent and tuple(floor(v/4096) for v in position[:2])!=parent["grid"]:
            raise ValueError("Placement is outside selected exterior cell")
        self.checkpoint()
        self.rows[key]={**row,"plugin":self.name,"position":tuple(position),"rotation":(0,0,yaw),"scale":scale}
        self.operations.append({"action":"transform_static","key":key_json(key),"position":position,"yaw_radians":yaw,"scale":scale})

    def export(self,path):
        payload={"version":1,"game":"new-vegas","kind":"world-edit-draft","draft_plugin":self.name,
                 "operations":self.operations,"native_plugin_written":False}
        with Path(path).open("x",encoding="utf-8") as stream:
            json.dump(payload,stream,indent=2,allow_nan=False)
