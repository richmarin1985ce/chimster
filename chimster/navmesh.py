"""Portable triangulated heightfield navigation; coordinates in caller's world units."""
import math,heapq
from collections import defaultdict,deque

def num(v,lo,hi):
    if type(v) not in (int,float) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError("invalid navigation parameter")
    return float(v)
def point(p):
    if len(p)!=3:raise ValueError("expected XYZ")
    return tuple(num(x,-1e7,1e7) for x in p)
def topology(vertices,triangles):
    vertices=[point(p) for p in vertices];triangles=list(triangles)
    if len(vertices)>1000000 or len(triangles)>2000000:raise ValueError("mesh limit")
    edges=defaultdict(list);neighbors=[[-1]*3 for _ in triangles];seen=set()
    for i,t in enumerate(triangles):
        if len(t)!=3 or any(type(v) is not int or not 0<=v<len(vertices) for v in t) or len(set(t))!=3:raise ValueError("invalid triangle indices")
        key=tuple(sorted(t))
        if key in seen:raise ValueError("duplicate triangle")
        seen.add(key);a,b,c=[vertices[v] for v in t]
        area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
        if area<=1e-12:raise ValueError("degenerate or reversed walkable triangle")
        for j,(u,v) in enumerate(zip(t,t[1:]+t[:1])):
            e=edges[tuple(sorted((u,v)))];e.append((i,j,u,v))
            if len(e)>2:raise ValueError("nonmanifold edge")
    boundary=[]
    for key,owners in edges.items():
        if len(owners)==1:boundary.append(key);continue
        (a,ea,u,v),(b,eb,x,y)=owners
        if (u,v)!=(y,x):raise ValueError("inconsistent winding")
        neighbors[a][ea]=b;neighbors[b][eb]=a
    groups=[];remaining=set(range(len(triangles)))
    while remaining:
        root=min(remaining);remaining.remove(root);q=deque([root]);group=[]
        while q:
            i=q.popleft();group.append(i)
            for j in neighbors[i]:
                if j in remaining:remaining.remove(j);q.append(j)
        groups.append(sorted(group))
    return {"neighbors":neighbors,"boundary":sorted(boundary),"regions":groups}
def generate(spec):
    """Single-layer sampled floor; never bridge missing samples or blocked cells.
    Whole cell footprint must be supported. Clearance erodes against blocked
    cells and the outer boundary. Obstacle boxes are explicit collision proxies.
    """
    if spec.get("schema")!=1:raise ValueError("unknown navmesh schema")
    if set(spec)-{"schema","origin","spacing","heights","ceilings","blocked","obstacles","agent","min_region_cells"}:raise ValueError("unknown navmesh input")
    origin=point(spec.get("origin",[0,0,0]));s=num(spec["spacing"],.001,1e6)
    h=spec["heights"];ny=len(h)-1;nx=len(h[0])-1 if h else -1
    if min(nx,ny)<1 or nx*ny>250000 or any(len(row)!=nx+1 for row in h):raise ValueError("invalid height grid")
    h=[[None if v is None else num(v,-1e7,1e7)+origin[2] for v in row] for row in h]
    agent=spec.get("agent",{})
    if set(agent)-{"radius","height","max_slope","max_step"}:raise ValueError("unknown agent setting")
    radius=num(agent.get("radius",.3),0,1e5);height=num(agent.get("height",1.8),.001,1e5)
    slope=num(agent.get("max_slope",45),0,89.9);step=num(agent.get("max_step",.4),0,1e5)
    ceiling=spec.get("ceilings")
    if ceiling is not None and (len(ceiling)!=ny or any(len(row)!=nx for row in ceiling)):raise ValueError("invalid ceiling grid")
    blocked=set()
    for p in spec.get("blocked",[]):
        if len(p)!=2 or any(type(i) is not int for i in p) or not 0<=p[0]<nx or not 0<=p[1]<ny:raise ValueError("invalid blocked cell")
        blocked.add(tuple(p))
    obstacles=[]
    for o in spec.get("obstacles",[]):
        lo,hi=point(o["min"]),point(o["max"])
        if any(a>=b for a,b in zip(lo,hi)):raise ValueError("invalid obstacle")
        obstacles.append((lo,hi))
    if len(obstacles)*nx*ny>20000000:raise ValueError("obstacle work limit; partition the scene")
    floor={};reject=defaultdict(int)
    limit=math.tan(math.radians(slope))
    for y in range(ny):
        for x in range(nx):
            k=(x,y);z=(h[y][x],h[y][x+1],h[y+1][x+1],h[y+1][x])
            if k in blocked or None in z:reject["missing_or_blocked"]+=1;continue
            a,b,c,d=z
            # Two triangles on the common diagonal. Exact gradient magnitude.
            if max(math.hypot(b-a,c-b),math.hypot(c-d,d-a))>s*limit+1e-9:reject["slope"]+=1;continue
            if max(abs(b-a),abs(c-b),abs(c-d),abs(d-a))>step+1e-9:reject["step"]+=1;continue
            if ceiling is not None and ceiling[y][x] is not None and num(ceiling[y][x],-1e7,1e7)+origin[2]-max(z)<height:reject["headroom"]+=1;continue
            xl=origin[0]+x*s;yl=origin[1]+y*s
            if any(lo[0]<xl+s+radius and hi[0]>xl-radius and lo[1]<yl+s+radius and hi[1]>yl-radius and lo[2]<max(z)+height and hi[2]>min(z)+1e-7 for lo,hi in obstacles):
                reject["obstacle"]+=1;continue
            floor[k]=z
    # Conservative distance from cell footprint to blocked cell footprint.
    reach=math.ceil(radius/s)+1
    if reach>128 or len(floor)*(2*reach+1)**2>50000000:raise ValueError("clearance work limit; increase spacing or tile input")
    valid=set(floor)
    if radius:
        offsets=[(dx,dy) for dy in range(-reach,reach+1) for dx in range(-reach,reach+1)
                 if math.hypot(max(0,abs(dx)-1)*s,max(0,abs(dy)-1)*s)<radius-1e-10]
        valid={k for k in floor if all((k[0]+dx,k[1]+dy) in floor for dx,dy in offsets)}
    reject["clearance"]=len(floor)-len(valid)
    minimum=spec.get("min_region_cells",1)
    if type(minimum) is not int or not 1<=minimum<=250000:raise ValueError("invalid region threshold")
    remaining=set(valid);kept=set()
    while remaining:
        root=min(remaining);remaining.remove(root);q=deque([root]);region={root}
        while q:
            x,y=q.popleft()
            for k in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if k in remaining:remaining.remove(k);region.add(k);q.append(k)
        if len(region)>=minimum:kept.update(region)
        else:reject["small_region"]+=len(region)
    vertices=[];triangles=[];index={}
    def vertex(x,y):
        k=(x,y)
        if k not in index:
            index[k]=len(vertices);vertices.append((origin[0]+x*s,origin[1]+y*s,h[y][x]))
        return index[k]
    for x,y in sorted(kept,key=lambda p:(p[1],p[0])):
        a,b,c,d=[vertex(*k) for k in ((x,y),(x+1,y),(x+1,y+1),(x,y+1))]
        triangles.extend(((a,b,c),(a,c,d)))
    report=topology(vertices,triangles)
    return {"schema":1,"vertices":vertices,"triangles":triangles,**report,"rejected":dict(reject),"walkable_cells":len(kept),"source_cells":nx*ny,"scope":"portable single-layer heightfield; collision proxies and conservative whole-cell clearance"}

def route(mesh,start,end,links=(),closed=()):
    """Triangle corridor with optional directed, named off-mesh links."""
    triangles=mesh["triangles"];vertices=mesh["vertices"]
    n=len(triangles)
    if type(start) is not int or type(end) is not int or not 0<=start<n or not 0<=end<n:raise ValueError("invalid route endpoints")
    graph=[[(j,None) for j in row if j>=0] for row in topology(vertices,triangles)["neighbors"]]
    closed=set(closed);names=set()
    for link in links:
        a,b=link["from"],link["to"];name=link["id"]
        if name in names or not 0<=a<n or not 0<=b<n or a==b:raise ValueError("invalid transition")
        names.add(name)
        if name not in closed:
            graph[a].append((b,name))
            if link.get("bidirectional",False):graph[b].append((a,name))
    if not closed<=names:raise ValueError("unknown closed link")
    centers=[tuple(sum(vertices[i][j] for i in t)/3 for j in range(3)) for t in triangles]
    q=[(0.,start)];cost={start:0.};prev={}
    while q:
        d,i=heapq.heappop(q)
        if d!=cost[i]:continue
        if i==end:
            path=[i];transitions=[]
            while i!=start:
                i,name=prev[i];path.append(i)
                if name is not None:transitions.append(name)
            return {"reachable":True,"triangles":path[::-1],"transitions":transitions[::-1],"cost":d}
        for j,name in graph[i]:
            nd=d+math.dist(centers[i],centers[j])
            if nd<cost.get(j,math.inf):cost[j]=nd;prev[j]=(i,name);heapq.heappush(q,(nd,j))
    return {"reachable":False,"triangles":[],"transitions":[],"cost":None}
