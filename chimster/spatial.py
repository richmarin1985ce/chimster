"""Immutable bounding-volume hierarchy for scene instances; conservative sphere culling."""
from dataclasses import dataclass
from math import sqrt
@dataclass(frozen=True)
class Entry:
    index:int
    instance:object
    center:tuple
    radius:float
@dataclass(frozen=True)
class Node:
    center:tuple
    radius:float
    count:int
    entries:tuple=()
    children:tuple=()

def build(entries,leaf_size=24):
    if not 1<=leaf_size<=128:raise ValueError("invalid leaf size")
    entries=tuple(entries)
    if not entries:return None
    lo=[min(e.center[k]-e.radius for e in entries) for k in range(3)]
    hi=[max(e.center[k]+e.radius for e in entries) for k in range(3)]
    center=tuple((a+b)*.5 for a,b in zip(lo,hi))
    radius=sqrt(sum(((b-a)*.5)**2 for a,b in zip(lo,hi)))
    if len(entries)<=leaf_size:return Node(center,radius,len(entries),entries)
    axis=max(range(3),key=lambda k:hi[k]-lo[k])
    sorted_entries=sorted(entries,key=lambda e:(e.center[axis],e.index))
    mid=len(entries)//2
    return Node(center,radius,len(entries),children=(build(sorted_entries[:mid],leaf_size),build(sorted_entries[mid:],leaf_size)))

def query(root,predicate):
    """Return visible entries and counters, preserving original order."""
    stats={"chunks_tested":0,"chunks_rejected":0,"objects_tested":0,"objects_rejected":0}
    out=[]
    def walk(n):
        if n is None:return
        stats["chunks_tested"]+=1
        if not predicate(n.center,n.radius):
            stats["chunks_rejected"]+=1;stats["objects_rejected"]+=n.count;return
        if n.children:
            for child in n.children:walk(child)
        else:
            for e in n.entries:
                stats["objects_tested"]+=1
                if predicate(e.center,e.radius):out.append(e)
                else:stats["objects_rejected"]+=1
    walk(root)
    return sorted(out,key=lambda e:e.index),stats
