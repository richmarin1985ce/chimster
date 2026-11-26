"""Portable discrete quadrant painting; explicit base textures, no alpha layers."""
from dataclasses import dataclass
from math import hypot,isfinite
@dataclass(frozen=True)
class Paint:
    rows:tuple
    def validate(self,cells):
        n=cells*2
        if len(self.rows)!=n or any(len(r)!=n for r in self.rows):raise ValueError("expected two quadrants per cell axis")
        if any(not isinstance(v,str) or not v for r in self.rows for v in r):raise ValueError("invalid texture ID")
        return self
    def brush(self,x,y,radius,material):
        if not all(isfinite(v) for v in (x,y,radius)) or radius<=0 or not isinstance(material,str) or not material:raise ValueError("invalid brush")
        return Paint(tuple(tuple(material if hypot(i-x,j-y)<=radius else v for i,v in enumerate(row)) for j,row in enumerate(self.rows)))
    def quadrants(self,x,y):
        return tuple(self.rows[2*y+dy][2*x+dx] for dy,dx in ((0,0),(0,1),(1,0),(1,1)))
