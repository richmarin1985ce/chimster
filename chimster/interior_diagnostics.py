"""Read-only connectivity diagnostics for portable interior projects."""
from collections import deque,defaultdict
from .interior_layout import validate,contains,bounds,point

def audit(project,entry=None,closed=()):
    cells={c["id"]:c for c in project["cells"]};issues=[];graph=defaultdict(set);places={}
    closed=set(closed);portals=set()
    def issue(code,cell,detail,severity="warning"):
        issues.append({"code":code,"cell":cell,"detail":detail,"severity":severity})
    for cid,c in cells.items():
        layout=c.get("layout",{"schema":1,"rooms":[]});report=validate(layout)
        for problem in report["issues"]:issue("layout",cid,problem,"error")
        rooms={r["id"]:bounds(r) for r in layout["rooms"]}
        for rid in rooms:graph[(cid,rid)]
        for p in layout.get("portals",[]):
            key=(cid,p["id"]);portals.add(key)
            if report["valid"] and key not in closed:
                a,b=((cid,r) for r in p["rooms"]);graph[a].add(b);graph[b].add(a)
        for p in c.get("placements",[]):
            key=cid+"/"+p["id"]
            if key in places:issue("duplicate-placement",cid,key,"error")
            pos=point(p["position"]);matches=[rid for rid,box in rooms.items() if contains(box,pos)]
            places[key]=(p,cid,matches)
            if rooms and not matches:issue("outside-room",cid,key)
    if not closed<=portals:raise ValueError("unknown closed portal")
    for key,(p,cid,matches) in places.items():
        linked=p.get("linked_ref")
        if linked is not None and (linked==key or linked not in places):issue("broken-linked-reference",cid,key,"error")
        tele=p.get("teleport")
        if tele is None:continue
        target=tele.get("target")
        if target==key or target not in places:
            issue("broken-teleport",cid,key,"error");continue
        other,other_cell,dest_rooms=places[target]
        if other.get("teleport",{}).get("target")!=key:issue("nonreciprocal-teleport",cid,key,"error");continue
        if not p.get("persistent") or not other.get("persistent"):issue("nonpersistent-teleport",cid,key,"error");continue
        arrival=point(tele["arrival"])
        arrivals=[r["id"] for r in cells[other_cell].get("layout",{}).get("rooms",[]) if contains(bounds(r),arrival)]
        if not arrivals:issue("arrival-outside-room",cid,key);continue
        if len(matches)!=1 or len(arrivals)!=1:
            issue("ambiguous-teleport-room",cid,key);continue
        graph[(cid,matches[0])].add((other_cell,arrivals[0]))
    def reach(start):
        seen={start};q=deque([start])
        while q:
            for n in graph[q.popleft()]:
                if n not in seen:seen.add(n);q.append(n)
        return seen
    nodes=set(graph)
    if entry is not None:
        entry=tuple(entry)
        if entry not in nodes:raise ValueError("unknown entry room")
    elif nodes:entry=min(nodes)
    reachable=reach(entry) if entry else set()
    for cid,rid in sorted(nodes-reachable):issue("unreachable-room",cid,rid)
    weak={n:set(v) for n,v in graph.items()}
    for n,links in graph.items():
        for v in links:weak[v].add(n)
    components=[];remaining=set(nodes)
    while remaining:
        root=min(remaining);component={root};q=deque([root])
        while q:
            for n in weak[q.popleft()]:
                if n not in component:component.add(n);q.append(n)
        remaining-=component;components.append(sorted(component))
    return {"valid":not any(x["severity"]=="error" for x in issues),"entry":entry,"reachable":sorted(reachable),
            "unreachable":sorted(nodes-reachable),"components":components,"issues":issues,
            "scope":"portable room connectivity and teleport arrivals, not navmesh or engine pathfinding"}
