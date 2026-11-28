"""Portable world LOD metadata; not a native TVDT encoder."""
from math import isfinite

def height_bounds(samples):
    low=float("inf");high=-low
    for row in samples:
        for v in row:
            if not isfinite(v):raise ValueError("Nonfinite terrain height")
            low=min(low,v);high=max(high,v)
    if not isfinite(low):raise ValueError("Empty terrain")
    return {"min_height":low,"max_height":high}

def dirty_tiles(cells,levels=(4,8,16,32)):
    out={}
    cells=list(cells)
    if any(type(x) is not int or type(y) is not int for x,y in cells):raise ValueError("Integer cell coordinates required")
    for n in levels:
        if n not in (4,8,16,32):raise ValueError("Unsupported LOD level")
        out[n]=sorted({(x//n*n,y//n*n) for x,y in cells})
    return out

def world_bounds(cells):
    cells=list(cells)
    if not cells:raise ValueError("Empty world")
    if any(type(x) is not int or type(y) is not int for x,y in cells):raise ValueError("Integer cell coordinates required")
    lo=tuple(min(p[i] for p in cells) for i in range(2))
    hi=tuple(max(p[i] for p in cells) for i in range(2))
    return {"min_cell":lo,"max_cell":hi,"min_world":tuple(x*4096 for x in lo),
            "max_world_exclusive":tuple((x+1)*4096 for x in hi),
            "occlusion_extent_warning":any(b-a+1>256 for a,b in zip(lo,hi))}
