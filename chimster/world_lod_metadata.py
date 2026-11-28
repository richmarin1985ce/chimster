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


def fnv_settings(cells,levels=(4,8,16,32),object_level=4):
    """24-byte FO3/FNV settings layout; inclusive cell bounds, stride 4.
    Values are candidate defaults until independently checked against a game file.
    """
    import struct
    bounds=world_bounds(cells)
    if not levels or any(v not in (4,8,16,32) for v in levels) or object_level not in (4,8,16,32):
        raise ValueError("Unsupported LOD level")
    lo,hi=bounds["min_cell"],bounds["max_cell"]
    if any(not -32768<=v<=32767 for v in (*lo,*hi)):raise ValueError("LODSettings coordinate limit")
    return struct.pack("<3I4hI",min(levels),max(levels),4,*lo,*hi,object_level)

def read_fnv_settings(raw):
    import struct
    if len(raw)!=24:raise ValueError("Invalid FO3/FNV settings size")
    low,high,stride,x,y,X,Y,obj=struct.unpack("<3I4hI",raw)
    if low not in (4,8,16,32) or high not in (4,8,16,32) or low>high or not stride or x>X or y>Y or obj not in (4,8,16,32):
        raise ValueError("Invalid LODSettings fields")
    return {"min_level":low,"max_level":high,"stride":stride,"min_cell":(x,y),"max_cell":(X,Y),"object_level":obj}


def skyrim_settings(cells,levels=(4,8,16,32),southwest=None):
    """16-byte classic Skyrim LOD quadtree settings candidate."""
    import struct
    bounds=world_bounds(cells);lo,hi=bounds["min_cell"],bounds["max_cell"]
    if not levels or any(v not in (4,8,16,32) for v in levels):raise ValueError("Unsupported LOD levels")
    origin=tuple(southwest) if southwest is not None else tuple(v//max(levels)*max(levels) for v in lo)
    if len(origin)!=2 or any(type(v)!=int or not -32768<=v<=32767 for v in origin) or any(origin[i]>lo[i] for i in range(2)):raise ValueError("Invalid southwest origin")
    size=max(levels)
    while any(origin[i]+size<=hi[i] for i in range(2)):size*=2
    if size>65536:raise ValueError("LOD quadtree extent limit")
    return struct.pack("<2h3I",*origin,size,min(levels),max(levels))

def read_skyrim_settings(raw):
    import struct
    if len(raw)!=16:raise ValueError("Invalid Skyrim LOD settings size")
    x,y,size,low,high=struct.unpack("<2h3I",raw)
    if low not in (4,8,16,32) or high not in (4,8,16,32) or low>high or size<high or size&(size-1) or size>65536:raise ValueError("Invalid Skyrim LOD settings")
    return {"southwest":(x,y),"stride":size,"min_level":low,"max_level":high}
