"""Solid obstacle proxy validation and conservative box queries."""
import math
def normalize(rows):
    if not isinstance(rows,(list,tuple)) or len(rows)>4096:raise ValueError("solid obstacle limit")
    result=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={"min","max"}:raise ValueError("invalid solid obstacle")
        lo,hi=row["min"],row["max"]
        if any(not isinstance(p,(list,tuple)) or len(p)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in p) for p in (lo,hi)) or any(a>=b for a,b in zip(lo,hi)):
            raise ValueError("invalid solid obstacle bounds")
        result.append({"min":tuple(float(v) for v in lo),"max":tuple(float(v) for v in hi)})
    return result

def overlaps(row,lo,hi):
    return all(row["min"][i]<hi[i] and row["max"][i]>lo[i] for i in range(3))
