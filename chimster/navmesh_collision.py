"""Conservative multi-layer collision-surface AutoNav rasterizer.

Z-up triangle soup, upward-facing walkable surfaces, explicit solid collision.
No implicit unit conversion or automatic bridging of holes.
"""
import math
from collections import defaultdict,deque
from .navmesh import point,num,topology

EPS=1e-7

def clip(poly,axis,value,sign):
    out=[]
    if not poly:return out
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=(a[axis]-value)*sign;db=(b[axis]-value)*sign
        if da>=-EPS:out.append(a)
        if (da>=-EPS)!=(db>=-EPS):
            t=da/(da-db)
            out.append(tuple(a[i]+t*(b[i]-a[i]) for i in range(3)))
    return out

def clipped(tri,x,y,s):
    p=list(tri)
    for axis,v,sign in ((0,x,1),(0,x+s,-1),(1,y,1),(1,y+s,-1)):
        p=clip(p,axis,v,sign)
    return p

def area(poly):
    if len(poly)<3:return 0.
    a=poly[0]
    return abs(sum((p[0]-a[0])*(q[1]-a[1])-(p[1]-a[1])*(q[0]-a[0])
                   for p,q in zip(poly,poly[1:]+poly[:1])))*.5

def union_area(polys):
    """Exact piecewise-linear vertical-slice union for convex clipped polygons."""
    if len(polys)>64:raise ValueError("dense collision column; refine spacing")
    lines=[];xs=set()
    for p in polys:
        xs.update(v[0] for v in p)
        for a,b in zip(p,p[1:]+p[:1]):
            if abs(a[0]-b[0])<=EPS:continue
            k=(b[1]-a[1])/(b[0]-a[0]);lo,hi=sorted((a[0],b[0]))
            lines.append((lo,hi,k,a[1]-k*a[0]))
    if len(lines)>512:raise ValueError("dense collision column; refine spacing")
    for i,(l,h,k,c) in enumerate(lines):
        for ll,hh,kk,cc in lines[i+1:]:
            if abs(k-kk)<=EPS:continue
            x=(cc-c)/(k-kk)
            if max(l,ll)<x<min(h,hh):xs.add(x)
    def length(x):
        intervals=[]
        for p in polys:
            ys=[]
            for a,b in zip(p,p[1:]+p[:1]):
                if min(a[0],b[0])<x<max(a[0],b[0]):
                    ys.append(a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0]))
            if len(ys)>=2:intervals.append((min(ys),max(ys)))
        total=0.;end=-math.inf
        for lo,hi in sorted(intervals):
            total+=max(0.,hi-max(lo,end));end=max(end,hi)
        return total
    xs=sorted(xs)
    return sum((b-a)*length((a+b)*.5) for a,b in zip(xs,xs[1:]) if b-a>EPS)

def generate_collision(spec):
    if spec.get("schema")!=1 or set(spec)-{"schema","vertices","triangles","spacing","agent","min_region_cells"}:
        raise ValueError("invalid collision navigation source")
    vs=[point(v) for v in spec["vertices"]];ts=spec["triangles"]
    if not vs or not ts or len(vs)>500000 or len(ts)>500000:raise ValueError("collision mesh size limit")
    s=num(spec["spacing"],.01,1e5)
    agent=spec.get("agent",{})
    if set(agent)-{"radius","height","max_slope","max_step"}:raise ValueError("unknown agent setting")
    radius=num(agent.get("radius",.3),0,1e5);height=num(agent.get("height",1.8),.001,1e5)
    slope=num(agent.get("max_slope",45),0,89.9);step=num(agent.get("max_step",.4),0,1e5)
    limit=math.tan(math.radians(slope))
    ox=math.floor(min(v[0] for v in vs)/s)*s;oy=math.floor(min(v[1] for v in vs)/s)*s
    columns=defaultdict(list);work=0
    for t in ts:
        if len(t)!=3 or any(type(i) is not int or not 0<=i<len(vs) for i in t) or len(set(t))!=3:raise ValueError("invalid collision indices")
        tri=[vs[i] for i in t];a,b,c=tri
        u=[b[i]-a[i] for i in range(3)];v=[c[i]-a[i] for i in range(3)]
        n=(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])
        if math.hypot(*n)<=EPS:continue
        plane=None
        if n[2]>EPS and math.hypot(n[0],n[1])<=n[2]*limit+EPS:
            px=-n[0]/n[2];py=-n[1]/n[2];pz=a[2]-px*(a[0]-ox)-py*(a[1]-oy)
            plane=(px,py,pz)
        x0=math.floor((min(p[0] for p in tri)-ox-EPS)/s);x1=math.floor((max(p[0] for p in tri)-ox+EPS)/s)
        y0=math.floor((min(p[1] for p in tri)-oy-EPS)/s);y1=math.floor((max(p[1] for p in tri)-oy+EPS)/s)
        work+=(x1-x0+1)*(y1-y0+1)
        if work>2000000:raise ValueError("raster work limit; use coarser spacing or tiles")
        for y in range(y0,y1+1):
            for x in range(x0,x1+1):
                poly=clipped(tri,ox+x*s,oy+y*s,s)
                if poly:columns[x,y].append((plane,poly))
    if len(columns)>250000:raise ValueError("column limit")
    candidates={};reject=defaultdict(int)
    def corners(k,plane):
        x,y=k;px,py,pz=plane
        return tuple(px*(x+dx)*s+py*(y+dy)*s+pz for dx,dy in ((0,0),(1,0),(1,1),(0,1)))
    for k,faces in sorted(columns.items()):
        groups=defaultdict(list)
        for plane,poly in faces:
            if plane is not None and area(poly)>EPS*s*s:
                groups[tuple(round(v,8) for v in plane)].append(poly)
        spans=[]
        for plane,polys in sorted(groups.items()):
            if union_area(polys)<s*s*(1-1e-7):
                reject["partial_surface"]+=1;continue
            z=corners(k,plane);low,high=min(z),max(z)
            # Other surfaces (including vertical walls) are conservative obstacles.
            blocked=False
            for other,poly in faces:
                if other is not None and tuple(round(v,8) for v in other)==plane:continue
                # Compare collision vertex height to the candidate floor at that XY.
                delta=[p[2]-(plane[0]*(p[0]-ox)+plane[1]*(p[1]-oy)+plane[2]) for p in poly]
                if max(delta)>EPS and min(delta)<height-EPS:
                    # A short riser strictly on the cell boundary is a possible
                    # step, not an interior obstacle. Tall walls still block.
                    x0=ox+k[0]*s;y0=oy+k[1]*s
                    on_edge=any(all(abs(p[axis]-v)<=EPS for p in poly) for axis,v in ((0,x0),(0,x0+s),(1,y0),(1,y0+s)))
                    if on_edge and max(delta)<=step+EPS:continue
                    blocked=True;break
            if blocked:reject["headroom_or_collision"]+=1;continue
            spans.append(z)
        if spans:candidates[k]=sorted(spans,key=lambda z:sum(z))
    if sum(map(len,candidates.values()))>500000:raise ValueError("layer limit")
    # Layer-aware conservative erosion. A neighboring span must be reachable
    # at corresponding edge heights; no upper floor can satisfy lower clearance.
    offsets=[]
    reach=math.ceil(radius/s)+1
    if reach>64 or sum(map(len,candidates.values()))*(2*reach+1)**2>30000000:raise ValueError("clearance work limit")
    if radius:
        offsets=[(dx,dy) for dx in range(-reach,reach+1) for dy in range(-reach,reach+1)
                 if math.hypot(max(0,abs(dx)-1)*s,max(0,abs(dy)-1)*s)<radius-EPS]
    def near(z,w,dx,dy):
        # Compare mean heights with allowance for continuous slopes over offset.
        return abs(sum(z)/4-sum(w)/4)<=step+limit*s*math.hypot(dx,dy)+EPS and abs(sum(z)/4-sum(w)/4)<height-EPS
    kept={}
    for k,spans in candidates.items():
        for i,z in enumerate(spans):
            if all(any(near(z,w,dx,dy) for w in candidates.get((k[0]+dx,k[1]+dy),[])) for dx,dy in offsets):
                kept[k[0],k[1],i]=z
            else:reject["clearance"]+=1
    vertices=[];triangles=[];ids={};layers=[];cell_tri={}
    def vert(x,y,z):
        key=(x,y,round(z,7))
        if key not in ids:
            ids[key]=len(vertices);vertices.append((ox+x*s,oy+y*s,key[2]))
        return ids[key]
    for key,z in sorted(kept.items()):
        x,y,i=key
        a,b,c,d=[vert(x+dx,y+dy,h) for (dx,dy),h in zip(((0,0),(1,0),(1,1),(0,1)),z)]
        cell_tri[key]=len(triangles);triangles.extend(((a,b,c),(a,c,d)));layers.extend((i,i))
    report=topology(vertices,triangles)
    # Stepped floors stay disconnected unless a full shared edge has a
    # bounded step. Both columns already passed conservative collision checks.
    links=[];by_xy=defaultdict(list)
    for key in kept:by_xy[key[:2]].append(key)
    for key,z in sorted(kept.items()):
        x,y,i=key
        for dx,dy,ea,eb,ta,tb in ((1,0,(1,2),(0,3),0,1),(0,1,(3,2),(0,1),1,0)):
            for dest in by_xy.get((x+dx,y+dy),[]):
                w=kept[dest];deltas=[abs(z[a]-w[b]) for a,b in zip(ea,eb)]
                if max(deltas)<=EPS or max(deltas)>step+EPS:continue
                # Avoid declaring a step when another sheet is already a direct continuation.
                a=cell_tri[key]+ta;b=cell_tri[dest]+tb
                if b in report["neighbors"][a]:continue
                links.append({"id":f"step:{x}:{y}:{i}:{dx}:{dy}:{dest[2]}","from":a,"to":b,
                              "bidirectional":True,"kind":"step","height_delta":max(deltas)})
    minimum=spec.get("min_region_cells",1)
    if type(minimum) is not int or not 1<=minimum<=250000:raise ValueError("invalid region threshold")
    # Region pruning uses both triangle adjacency and explicit step links.
    if minimum>1 and triangles:
        graph=[set(j for j in row if j>=0) for row in report["neighbors"]]
        for l in links:graph[l["from"]].add(l["to"]);graph[l["to"]].add(l["from"])
        seen=set();keep=set()
        for i in range(len(triangles)):
            if i in seen:continue
            seen.add(i);q=deque([i]);region=[]
            while q:
                j=q.popleft();region.append(j)
                for n in graph[j]:
                    if n not in seen:seen.add(n);q.append(n)
            if len(region)>=2*minimum:keep.update(region)
            else:reject["small_region"]+=len(region)//2
        ordered=sorted(keep);mapping={i:j for j,i in enumerate(ordered)}
        triangles=[triangles[i] for i in ordered];layers=[layers[i] for i in ordered]
        links=[{**l,"from":mapping[l["from"]],"to":mapping[l["to"]]} for l in links if l["from"] in keep and l["to"] in keep]
        report=topology(vertices,triangles)
    return {"schema":1,"vertices":vertices,"triangles":triangles,**report,"links":links,
            "triangle_layers":layers,"walkable_cells":len(triangles)//2,"source_columns":len(columns),
            "rejected":dict(reject),"scope":"portable multi-layer collision rasterization; coplanar full-cell coverage; conservative headroom and clearance; explicit step transitions"}
