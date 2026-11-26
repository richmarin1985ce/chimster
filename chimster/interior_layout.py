"""Portable room/portal/trigger/node layout checks, not native record output."""
from math import isfinite
from collections import deque
def point(p):
    if not isinstance(p,(tuple,list)) or len(p)!=3 or not all(type(v) in (int,float) and isfinite(v) and abs(v)<=1e7 for v in p):raise ValueError("invalid point")
    return tuple(p)
def bounds(b):
    lo,hi=point(b["min"]),point(b["max"])
    if any(a>=c for a,c in zip(lo,hi)):raise ValueError("degenerate volume")
    return lo,hi
def contains(box,p,tol=1e-6):
    return all(a-tol<=v<=b+tol for a,b,v in zip(*box,p))
def index(rows):
    result={}
    for r in rows:
        k=r["id"]
        if not isinstance(k,str) or not k or k in result:raise ValueError("duplicate or invalid ID")
        result[k]=r
    return result
def validate(layout):
    if layout.get("schema")!=1:raise ValueError("unknown layout schema")
    if any(len(layout.get(k,[]))>10000 for k in ("rooms","portals","triggers","nodes")):raise ValueError("layout limit")
    rooms={k:bounds(v) for k,v in index(layout["rooms"]).items()}
    portals=index(layout.get("portals",[]));triggers=index(layout.get("triggers",[]));nodes=index(layout.get("nodes",[]))
    adjacency={k:set() for k in rooms};issues=[]
    for id,p in portals.items():
        a,b=p["rooms"]
        if a==b or a not in rooms or b not in rooms:issues.append(f"{id}: invalid room links");continue
        corners=[point(v) for v in p["corners"]]
        if len(corners)!=4 or len(set(corners))!=4:issues.append(f"{id}: expected four distinct corners");continue
        # Axis-aligned rectangle on the shared boundary of the two rooms.
        axes=[i for i in range(3) if max(v[i] for v in corners)-min(v[i] for v in corners)<=1e-6]
        if len(axes)!=1:issues.append(f"{id}: invalid portal plane");continue
        axis=axes[0];v=corners[0][axis];other=[i for i in range(3) if i!=axis]
        expected={(u,w) for u in (min(c[i] for c in corners for i in [other[0]]),max(c[other[0]] for c in corners)) for w in (min(c[other[1]] for c in corners),max(c[other[1]] for c in corners))}
        shared=(abs(v-rooms[a][1][axis])<=1e-6 and abs(v-rooms[b][0][axis])<=1e-6 or abs(v-rooms[b][1][axis])<=1e-6 and abs(v-rooms[a][0][axis])<=1e-6)
        if not shared or {(c[other[0]],c[other[1]]) for c in corners}!=expected or not all(contains(rooms[a],c) and contains(rooms[b],c) for c in corners):
            issues.append(f"{id}: portal not on shared room boundary");continue
        adjacency[a].add(b);adjacency[b].add(a)
    for id,t in triggers.items():
        lo,hi=bounds(t);room=t.get("room")
        if room not in rooms or not contains(rooms[room],lo) or not contains(rooms[room],hi):issues.append(f"{id}: trigger outside owning room")
        if not isinstance(t.get("event"),str) or not t["event"]:issues.append(f"{id}: missing trigger event")
    for id,n in nodes.items():
        p=point(n["position"]);room=n.get("room")
        if room not in rooms or not contains(rooms[room],p):issues.append(f"{id}: node outside owning room")
        for link in n.get("links",[]):
            if link not in nodes or link==id:issues.append(f"{id}: invalid node link {link}")
            elif nodes[link].get("room")!=room and nodes[link].get("room") not in adjacency.get(room,set()):issues.append(f"{id}: cross-room node link lacks portal")
    return {"valid":not issues,"issues":issues,"rooms":len(rooms),"portals":len(portals),"triggers":len(triggers),"nodes":len(nodes),"adjacency":{k:sorted(v) for k,v in adjacency.items()},"scope":"portable axis-aligned layout, not native engine records or navmesh"}
def candidates(layout,room,closed=()):
    report=validate(layout)
    if not report["valid"]:raise ValueError("invalid room layout")
    if room not in report["adjacency"]:raise ValueError("unknown camera room")
    blocked=set(closed);known={p["id"] for p in layout.get("portals",[])}
    if not blocked<=known:raise ValueError("unknown closed portal")
    graph={k:set() for k in report["adjacency"]}
    for p in layout.get("portals",[]):
        if p["id"] not in blocked:
            a,b=p["rooms"];graph[a].add(b);graph[b].add(a)
    visible={room};queue=deque([room])
    while queue:
        for n in graph[queue.popleft()]:
            if n not in visible:visible.add(n);queue.append(n)
    return {"visible_candidates":sorted(visible),"culled_disconnected":sorted(set(graph)-visible),"scope":"conservative connectivity only; no portal frustum clipping"}
