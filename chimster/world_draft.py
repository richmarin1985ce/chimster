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
