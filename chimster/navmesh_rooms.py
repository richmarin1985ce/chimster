"""Generate separate walkable room meshes and explicit door/portal transitions."""
import math
from .interior_layout import validate,bounds,point
from .navmesh import generate,topology,num

def build(layout,spacing,agent=None,obstacles=(),portal_doors=None):
    report=validate(layout)
    if not report["valid"]:raise ValueError("invalid interior layout")
    spacing=num(spacing,.001,1e6);agent=dict(agent or {})
    radius=num(agent.get("radius",.3),0,1e5);height=num(agent.get("height",1.8),.001,1e5)
    portal_doors=portal_doors or {}
    rooms={r["id"]:bounds(r) for r in layout["rooms"]}
    portals={p["id"]:p for p in layout.get("portals",[])}
    if not set(portal_doors)<=portals.keys():raise ValueError("unknown portal binding")
    obstacles=list(obstacles)
    vertices=[];triangles=[];owner=[];links=[];issues=[];stats={}
    # Each room gets its own vertices, even where coordinates coincide.
    # Cross-wall travel is only possible via explicitly declared openings.
    for rid,(lo,hi) in sorted(rooms.items()):
        nx=math.floor((hi[0]-lo[0])/spacing);ny=math.floor((hi[1]-lo[1])/spacing)
        if nx<1 or ny<1 or hi[2]-lo[2]<height:
            issues.append({"room":rid,"code":"insufficient-room-clearance"});continue
        if nx*ny>250000 or len(triangles)+2*nx*ny>500000:raise ValueError("room generation budget; increase spacing")
        mesh=generate({"schema":1,"origin":lo,"spacing":spacing,"heights":[[0.]*(nx+1) for _ in range(ny+1)],
                       "agent":agent,"obstacles":obstacles})
        offset=len(vertices);vertices.extend(mesh["vertices"])
        triangles.extend(tuple(v+offset for v in t) for t in mesh["triangles"])
        owner.extend([rid]*len(mesh["triangles"]));stats[rid]=mesh["walkable_cells"]
        if not mesh["triangles"]:issues.append({"room":rid,"code":"no-walkable-floor"})
    centers=[tuple(sum(vertices[i][j] for i in t)/3 for j in range(3)) for t in triangles]
    by_room={r:[] for r in rooms}
    for i,r in enumerate(owner):by_room[r].append(i)
    boxes=[(point(o["min"]),point(o["max"])) for o in obstacles]
    max_step=num(agent.get("max_step",.4),0,1e5)
    for pid,p in sorted(portals.items()):
        a,b=p["rooms"];corners=p["corners"]
        lo=[min(v[i] for v in corners) for i in range(3)];hi=[max(v[i] for v in corners) for i in range(3)]
        fixed=[i for i in range(3) if hi[i]-lo[i]<1e-6]
        if len(fixed)!=1 or fixed[0]==2:
            issues.append({"portal":pid,"code":"nonvertical-opening"});continue
        horizontal=1-fixed[0]
        if hi[horizontal]-lo[horizontal]<2*radius or hi[2]-lo[2]<height:
            issues.append({"portal":pid,"code":"opening-too-small"});continue
        if any(abs(rooms[r][0][2]-lo[2])>max_step for r in (a,b)):
            issues.append({"portal":pid,"code":"opening-step-too-high"});continue
        center=[(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]]
        endpoints=[]
        for r in (a,b):
            if not by_room[r]:break
            i=min(by_room[r],key=lambda j:math.dist(centers[j],center))
            if math.dist(centers[i],center)>radius+3*spacing+max_step:break
            # Reject a transition whose swept bounding prism intersects an obstacle.
            start=centers[i];lower=[min(start[k],center[k])-radius for k in (0,1)]
            upper=[max(start[k],center[k])+radius for k in (0,1)]
            zlo=min(start[2],center[2]);zhi=max(start[2],center[2])+height
            if any(o[0][0]<upper[0] and o[1][0]>lower[0] and o[0][1]<upper[1] and o[1][1]>lower[1] and o[0][2]<zhi and o[1][2]>zlo+1e-7 for o in boxes):break
            endpoints.append(i)
        if len(endpoints)!=2:
            issues.append({"portal":pid,"code":"no-clear-transition"});continue
        links.append({"id":pid,"from":endpoints[0],"to":endpoints[1],"bidirectional":True,"door":portal_doors.get(pid)})
    return {"schema":1,"vertices":vertices,"triangles":triangles,**topology(vertices,triangles),
            "triangle_rooms":owner,"links":links,"room_cells":stats,"issues":issues,
            "scope":"portable room-floor mesh; no arbitrary multilayer collision rasterization or native runtime export"}
