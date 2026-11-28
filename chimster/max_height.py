"""Regeneration intermediate in game units; native MHDT packing not yet verified."""
from math import isfinite, floor, ceil
import struct

def decode_land(raw):
    if len(raw)!=1096:raise ValueError("Expected 33x33 VHGT")
    base=struct.unpack_from("<f",raw)[0]
    if not isfinite(base):raise ValueError("Invalid height offset")
    delta=struct.unpack_from("<1089b",raw,4)
    rows=[]
    for y in range(33):
        base+=delta[y*33];h=base;row=[h*8]
        for x in range(1,33):
            h+=delta[y*33+x];row.append(h*8)
        rows.append(row)
    return rows

def regenerate(cells,objects=(),resolution=8):
    """cells: {(cell_x,cell_y): 33x33 heights}; objects: world-space AABB pairs.
    Include all intersecting terrain vertices and object tops; do not treat missing cells as zero.
    """
    if resolution not in (1,2,4,8,16,32):raise ValueError("Invalid resolution")
    stride=32//resolution;size=4096/resolution
    result={}
    for key,rows in cells.items():
        if len(key)!=2 or any(type(v)!=int for v in key):raise ValueError("Invalid cell coordinates")
        if len(rows)!=33 or any(len(r)!=33 or not all(isfinite(h) for h in r) for r in rows):raise ValueError("Invalid landscape")
        result[key]={"min_terrain":min(map(min,rows)),"max_terrain":max(map(max,rows)),
          "upper_grid":[[max(rows[y][x] for y in range(j*stride,(j+1)*stride+1) for x in range(i*stride,(i+1)*stride+1)) for i in range(resolution)] for j in range(resolution)]}
    missing=set()
    for lo,hi in objects:
        if len(lo)!=3 or len(hi)!=3 or not all(isfinite(v) for v in (*lo,*hi)) or any(a>b for a,b in zip(lo,hi)):raise ValueError("Invalid object bounds")
        a,b=floor(lo[0]/4096),floor(hi[0]/4096);c,d=floor(lo[1]/4096),floor(hi[1]/4096)
        if (b-a+1)*(d-c+1)>65536:raise ValueError("Object coverage too large")
        for cy in range(c,d+1):
            for cx in range(a,b+1):
                if (cx,cy) not in result:missing.add((cx,cy));continue
                grid=result[cx,cy]["upper_grid"]
                for y in range(resolution):
                    for x in range(resolution):
                        px=cx*4096+x*size;py=cy*4096+y*size
                        if px<=hi[0] and px+size>=lo[0] and py<=hi[1] and py+size>=lo[1]:
                            grid[y][x]=max(grid[y][x],hi[2])
    for row in result.values():row["max_height"]=max(map(max,row["upper_grid"]))
    return {"cells":result,"missing_object_cells":sorted(missing),"resolution":resolution,"native_encoded":False}
