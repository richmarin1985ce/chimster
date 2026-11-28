"""Conservative hierarchical visibility for static spatial bounds."""
from dataclasses import dataclass
from .interior_layout import point
from .portal_clip import dot
from math import isfinite,sqrt

@dataclass(frozen=True)
class Node:
    lo:tuple
    hi:tuple
    ids:tuple=()
    children:tuple=()

def build(items,leaf_size=16):
    if not 1<=leaf_size<=256:raise ValueError("Invalid leaf size")
    rows=[];seen=set()
    for key,lo,hi in items:
        if not isinstance(key,str) or key in seen:raise ValueError("Invalid object ID")
        seen.add(key);lo,hi=point(lo),point(hi)
        if any(a>b for a,b in zip(lo,hi)):raise ValueError("Invalid bounds")
        rows.append((key,lo,hi))
    def split(rows):
        lo=tuple(min(r[1][i] for r in rows) for i in range(3))
        hi=tuple(max(r[2][i] for r in rows) for i in range(3))
        if len(rows)<=leaf_size:return Node(lo,hi,tuple(r[0] for r in rows))
        axis=max(range(3),key=lambda i:hi[i]-lo[i])
        rows.sort(key=lambda r:(r[1][axis]+r[2][axis],r[0]))
        mid=len(rows)//2
        return Node(lo,hi,children=(split(rows[:mid]),split(rows[mid:])))
    return split(rows) if rows else None

def query(root,planes):
    normalized=[]
    for n,d in planes:
        n=point(n);length=sqrt(dot(n,n))
        if length<1e-12 or not isfinite(d):raise ValueError("Invalid plane")
        normalized.append((tuple(v/length for v in n),d/length))
    visible=[];tested=0;rejected=0
    stack=[(root,tuple(normalized))] if root else []
    while stack:
        node,active=stack.pop();tested+=1;remaining=[]
        for n,d in active:
            upper=sum(v*(b if v>=0 else a) for v,a,b in zip(n,node.lo,node.hi))+d
            if upper < -1e-6:
                rejected+=1;break
            lower=sum(v*(a if v>=0 else b) for v,a,b in zip(n,node.lo,node.hi))+d
            if lower < 1e-6:remaining.append((n,d))
        else:
            visible.extend(node.ids)
            stack.extend((child,tuple(remaining)) for child in node.children)
    return {"visible_candidates":sorted(visible),"nodes_tested":tested,"nodes_rejected":rejected}
