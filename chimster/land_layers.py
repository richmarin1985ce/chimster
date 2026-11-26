"""Explicit sparse FNV alpha layers, using 17x17 quadrant vertex positions."""
import struct,math
from .fnv_patch import sub

def encode_layers(layers,texture_ids,cells):
    by_cell={};seen=set();counts={}
    for spec in layers:
        x,y=spec["cell"];q=spec["quadrant"];layer=spec["layer"];tex=spec["texture"]
        if any(type(v) is not int for v in (x,y,q,layer)) or not 0<=x<cells or not 0<=y<cells or not 0<=q<=3 or not 0<=layer<=3:raise ValueError("invalid cell, quadrant or layer (conservative 4-layer limit)")
        key=(x,y,q,layer)
        if key in seen:raise ValueError("duplicate alpha layer")
        seen.add(key)
        if tex not in texture_ids:raise ValueError("unknown alpha texture")
        points=spec["vertices"]
        if not isinstance(points,list) or not 1<=len(points)<=289:raise ValueError("invalid alpha vertex list")
        values={}
        for pos,alpha in points:
            if type(pos) is not int or not 0<=pos<289 or pos in values or not math.isfinite(alpha) or not 0<=alpha<=1:raise ValueError("invalid or duplicate alpha vertex")
            values[pos]=alpha
        encoded=sub(b"ATXT",struct.pack("<IBBh",texture_ids[tex],q,0,layer))+sub(b"VTXT",b"".join(struct.pack("<H2xf",pos,a) for pos,a in sorted(values.items())))
        by_cell.setdefault((x,y),[]).append((q,layer,encoded))
        counts[(x,y,q)]=counts.get((x,y,q),0)+1
    for x,y,q in counts:
        if {l for a,b,c,l in seen if (a,b,c)==(x,y,q)}!=set(range(counts[x,y,q])):raise ValueError("alpha layer indices must be contiguous from zero")
    return {k:b"".join(e for _,_,e in sorted(v)) for k,v in by_cell.items()}
