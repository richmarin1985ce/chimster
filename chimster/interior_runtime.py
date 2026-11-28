"""Portable trigger enter/exit events and conservative first-portal frustum filtering."""
from .interior_layout import validate,bounds,contains,point
from collections import deque
from math import isfinite
class Triggers:
    def __init__(self,layout):
        if not validate(layout)["valid"]:raise ValueError("invalid layout")
        self.volumes=[(r["id"],bounds(r),r["event"]) for r in layout.get("triggers",[])]
        self.inside=set()
    def update(self,position):
        p=point(position);now={i for i,b,_ in self.volumes if contains(b,p)}
        events=[{"id":i,"event":e,"phase":"enter" if i in now else "exit"} for i,b,e in self.volumes if (i in now)!=(i in self.inside)]
        self.inside=now;return events
def visible(layout,room,planes,closed=()):
    """Initial camera frustum planes (nx,ny,nz,d), inside >=0. Reject portals
    entirely outside any plane, then flood all potentially visible rooms.
    Not recursive portal-aperture clipping; never cull based on occluder geometry."""
    r=validate(layout)
    if not r["valid"] or room not in r["adjacency"]:raise ValueError("invalid layout/camera room")
    if len(planes)>6 or any(len(p)!=4 or not all(isfinite(v) for v in p) or not any(p[:3]) for p in planes):raise ValueError("invalid frustum")
    blocked=set(closed)
    if not blocked<={p["id"] for p in layout.get("portals",[])}:raise ValueError("unknown portal")
    graph={k:set() for k in r["adjacency"]};rejected=[]
    for p in layout.get("portals",[]):
        if p["id"] in blocked:continue
        if any(all(sum(plane[i]*c[i] for i in range(3))+plane[3]<-1e-6 for c in p["corners"]) for plane in planes):
            rejected.append(p["id"]);continue
        a,b=p["rooms"];graph[a].add(b);graph[b].add(a)
    found={room};q=deque(found)
    while q:
        for n in graph[q.popleft()]:
            if n not in found:found.add(n);q.append(n)
    return {"visible_candidates":sorted(found),"culled":sorted(set(graph)-found),"outside_frustum_portals":sorted(rejected),"scope":"conservative frustum-plane portal rejection; no recursive aperture clipping or renderer integration"}

def door_visibility(layout,cell,bindings,door_states,room,eye,planes=(),budget=4096):
    """Preview visibility with explicitly known open/closed native door identities.
    Missing state is treated as open for conservative rendering. IDs are plugin-local.
    """
    known={p["id"] for p in layout.get("portals",[])}
    mapping={}
    for entry in bindings:
        if entry["cell"]!=cell:continue
        pid=entry["portal"];local=entry["local_id"]
        if pid not in known or pid in mapping or type(local) is not int or not 0<local<=0xffffff:
            raise ValueError("invalid portal binding")
        mapping[pid]=local
    if any(type(state) is not bool for state in door_states.values()):
        raise ValueError("door states must be boolean open flags")
    blocked=[pid for pid,local in mapping.items() if door_states.get(local) is False]
    from .portal_clip import visible
    return {**visible(layout,room,eye,planes,blocked,budget),"closed_portals":sorted(blocked),
            "scope":"portable visibility preview, not live game door state"}
