"""Conservative planar fan removal. Never change mesh boundaries or link endpoints."""
from collections import defaultdict
from .navmesh import topology
import math

def simplify(mesh,budget=20000):
    if type(budget) is not int or not 0<=budget<=100000:raise ValueError("invalid simplification budget")
    vs=[tuple(p) for p in mesh["vertices"]];ts={i:tuple(t) for i,t in enumerate(mesh["triangles"])}
    before=topology(vs,list(ts.values()));initial=len(ts)
    keys=[k for k in ("triangle_layers","triangle_rooms","triangle_areas","triangle_tiles") if k in mesh]
    meta={i:tuple(mesh[k][i] for k in keys) for i in ts}
    protected={i for link in mesh.get("links",[]) for i in (link["from"],link["to"])}
    fixed={v for edge in before["boundary"] for v in edge}|{v for i in protected for v in ts[i]}
    if "triangle_tiles" in mesh:
        for i,row in enumerate(before["neighbors"]):
            for j in row:
                if j>=0 and mesh["triangle_tiles"][i]!=mesh["triangle_tiles"][j]:fixed.update(set(ts[i])&set(ts[j]))
    incident=defaultdict(set)
    for i,t in ts.items():
        for v in t:incident[v].add(i)
    def cross(a,b,c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def intersects(a,b,c,d):
        # Reject any intersection or collinear contact of nonadjacent edges.
        if any(max(a[k],b[k])<min(c[k],d[k])-1e-10 or max(c[k],d[k])<min(a[k],b[k])-1e-10 for k in (0,1)):return False
        return cross(a,b,c)*cross(a,b,d)<=1e-20 and cross(c,d,a)*cross(c,d,b)<=1e-20
    next_id=len(ts);removed=0;attempts=0
    for v in sorted(incident):
        if attempts>=budget:break
        if v in fixed:continue
        fan=sorted(incident[v])
        if not 3<=len(fan)<=32 or len({meta[i] for i in fan})!=1:continue
        attempts+=1
        edges={}
        for i in fan:
            t=ts[i];j=t.index(v);a,b=t[(j+1)%3],t[(j+2)%3]
            if a in edges:break
            edges[a]=b
        if len(edges)!=len(fan):continue
        start=min(edges);ring=[start];cur=edges[start]
        while cur!=start and cur in edges and cur not in ring:
            ring.append(cur);cur=edges[cur]
        if cur!=start or len(ring)!=len(fan):continue
        # Concave rings are allowed only when the projected boundary is simple.
        n=len(ring)
        if any(intersects(vs[ring[j]],vs[ring[(j+1)%n]],vs[ring[k]],vs[ring[(k+1)%n]])
               for j in range(n) for k in range(j+2,n) if (k+1)%n!=j):continue
        a,b,c=(vs[x] for x in ts[fan[0]])
        d=cross(a,b,c)
        if d<=0:continue
        px=((b[2]-a[2])*(c[1]-a[1])-(c[2]-a[2])*(b[1]-a[1]))/d
        py=((b[0]-a[0])*(c[2]-a[2])-(c[0]-a[0])*(b[2]-a[2]))/d
        if any(abs(vs[x][2]-(a[2]+px*(vs[x][0]-a[0])+py*(vs[x][1]-a[1])))>1e-6 for x in ring+[v]):continue
        # Ear clipping preserves all ring edges, including collinear boundary vertices.
        work=ring[:];new=[]
        while len(work)>3:
            ear=None
            for j in range(len(work)):
                x,y,z=work[j-1],work[j],work[(j+1)%len(work)]
                if cross(vs[x],vs[y],vs[z])<=1e-10:continue
                if any(all(cross(vs[p],vs[q],vs[w])>=-1e-10 for p,q in ((x,y),(y,z),(z,x))) for w in work if w not in (x,y,z)):continue
                ear=j;new.append((x,y,z));break
            if ear is None:break
            work.pop(ear)
        if len(work)!=3 or cross(*(vs[w] for w in work))<=1e-10:continue
        new.append(tuple(work))
        if len(new)>=len(fan):continue
        old_area=sum(cross(*(vs[w] for w in ts[i])) for i in fan)
        new_area=sum(cross(*(vs[w] for w in t)) for t in new)
        if not math.isclose(old_area,new_area,rel_tol=1e-9,abs_tol=1e-9):continue
        # A new internal diagonal must not already belong to unrelated faces.
        boundary={tuple(sorted((ring[j],ring[(j+1)%n]))) for j in range(n)}
        diagonals={tuple(sorted((t[j],t[(j+1)%3]))) for t in new for j in range(3)}-boundary
        if any((incident[a]&incident[b])-set(fan) for a,b in diagonals):continue
        value=meta[fan[0]]
        for i in fan:
            for w in ts[i]:incident[w].discard(i)
            del ts[i];del meta[i]
        for t in new:
            i=next_id;next_id+=1;ts[i]=t;meta[i]=value
            for w in t:incident[w].add(i)
        removed+=1
    ordered=sorted(ts);mapping={old:new for new,old in enumerate(ordered)}
    triangles=[ts[i] for i in ordered];after=topology(vs,triangles)
    if before["boundary"]!=after["boundary"] or len(before["regions"])!=len(after["regions"]):
        raise ValueError("simplification failed boundary/connectivity verification")
    result={**mesh,"triangles":triangles,**after,"links":[{**l,"from":mapping[l["from"]],"to":mapping[l["to"]]} for l in mesh.get("links",[])]}
    for j,k in enumerate(keys):result[k]=[meta[i][j] for i in ordered]
    if "triangle_areas" in result:
        from collections import Counter
        result["area_report"]={**result.get("area_report",{}),"counts":dict(Counter(result["triangle_areas"]))}
    result["simplification"]={"input_triangles":initial,"output_triangles":len(triangles),"removed_vertices":removed,"attempts":attempts}
    return result
