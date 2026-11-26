"""Portable terrain model with reversible sculpting and FNV cell slicing."""
from math import isfinite,hypot
from dataclasses import dataclass
import json
from pathlib import Path
CELL=32
@dataclass(frozen=True)
class Terrain:
    heights:tuple
    spacing_m:float=1.
    datum_m:float=0.
    def validate(self):
        n=len(self.heights)
        if n<33 or n>513 or (n-1)%32 or any(len(r)!=n for r in self.heights):raise ValueError("grid must be square 32*cells+1, max 513")
        if not isfinite(self.spacing_m) or self.spacing_m<=0 or not isfinite(self.datum_m):raise ValueError("invalid scale/datum")
        if any(not isfinite(v) or abs(v)>1e6 for r in self.heights for v in r):raise ValueError("invalid height")
        return self
    @property
    def cells(self):return (len(self.heights)-1)//32
    def cell(self,x,y):
        if not 0<=x<self.cells or not 0<=y<self.cells:raise ValueError("invalid cell")
        return tuple(tuple(r[x*32:x*32+33]) for r in self.heights[y*32:y*32+33])
    def sculpt(self,x,y,radius,delta):
        if not all(isfinite(v) for v in (x,y,radius,delta)) or radius<=0:raise ValueError("invalid brush")
        rows=[]
        for j,r in enumerate(self.heights):
            rows.append(tuple(z+delta*max(0.,1-hypot(i-x,j-y)/radius)**2 for i,z in enumerate(r)))
        return Terrain(tuple(rows),self.spacing_m,self.datum_m).validate()
    @classmethod
    def load(cls,path,spacing_m,datum_m=None):
        p=Path(path)
        if p.stat().st_size>16*1024*1024:raise ValueError("heightmap too large")
        rows=tuple(tuple(r) for r in json.loads(p.read_text(encoding="utf-8")))
        if not rows or any(not r for r in rows):raise ValueError("empty grid")
        return cls(rows,spacing_m,min(map(min,rows)) if datum_m is None else datum_m).validate()

class TerrainHistory:
    def __init__(self,terrain):
        self.current=terrain.validate();self.past=[];self.future=[]
    def sculpt(self,*args):
        next=self.current.sculpt(*args);self.past.append(self.current);self.past=self.past[-10:];self.future=[];self.current=next
    def undo(self):
        if self.past:self.future.append(self.current);self.current=self.past.pop()
    def redo(self):
        if self.future:self.past.append(self.current);self.current=self.future.pop()
