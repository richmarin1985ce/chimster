"""Incremental collision AutoNav tiles with global raster alignment and halo review.

Cache is project-local generated data, not an interchange format or native NAVM.
Rebuilds are transactional: old cache is never mutated.
"""
import hashlib,json,math
from collections import defaultdict
from .navmesh import num,point,topology
from .navmesh_collision import generate_collision

VERSION=3

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def tile_key(x,y):return f"{x},{y}"

def build(spec,previous=None,tile_cells=32):
    if spec.get("schema")!=1 or set(spec)-{"schema","vertices","triangles","spacing","agent","min_region_cells","solid_obstacles"}:
        raise ValueError("expected collision triangle source")
    if spec.get("min_region_cells",1)!=1:raise ValueError("tile-local region pruning is unsafe; use 1")
    if type(tile_cells) is not int or not 8<=tile_cells<=128:raise ValueError("tile size must be 8–128 cells")
    spacing=num(spec["spacing"],.01,1e5);agent=dict(spec.get("agent",{}))
    radius=num(agent.get("radius",.3),0,1e5)
    # Clearance and step sweeps both need source geometry outside the core.
    halo=max(4,math.ceil(radius/spacing)+3)
    if halo>64:raise ValueError("halo too large; increase spacing")
    size=tile_cells*spacing
    settings={"version":VERSION,"spacing":spacing,"tile_cells":tile_cells,"agent":agent,"halo":halo}
    settings_hash=digest(settings)
    vs=[point(v) for v in spec["vertices"]];ts=spec["triangles"]
    if not vs or not ts or max(len(vs),len(ts))>500000:raise ValueError("source size limit")
    buckets=defaultdict(list);work=0
    for t in ts:
        if len(t)!=3 or len(set(t))!=3 or any(type(v) is not int or not 0<=v<len(vs) for v in t):raise ValueError("invalid source triangle")
        tri=tuple(vs[v] for v in t)
        lo=[min(v[i] for v in tri) for i in (0,1)];hi=[max(v[i] for v in tri) for i in (0,1)]
        # Include every tile whose expanded raster window intersects this face.
        a,b=[math.floor((lo[i]-halo*spacing-1e-7)/size) for i in (0,1)]
        c,d=[math.floor((hi[i]+halo*spacing+1e-7)/size) for i in (0,1)]
        work+=(c-a+1)*(d-b+1)
        if work>2000000:raise ValueError("tile assignment budget")
        for y in range(b,d+1):
            for x in range(a,c+1):buckets[x,y].append(tri)
    if len(buckets)>4096:raise ValueError("tile count limit; partition the world")
    from .collision_obstacles import normalize
    solids=normalize(spec.get("solid_obstacles",[]))
    if len(solids)*len(buckets)>4000000:raise ValueError("tile obstacle assignment limit")
    old=previous.get("tiles",{}) if previous and previous.get("settings_hash")==settings_hash else {}
    tiles={};rebuilt=[];reused=[]
    for (x,y),faces in sorted(buckets.items()):
        key=tile_key(x,y)
        # Order independent of source vertex IDs or face list order; preserve winding.
        faces=sorted(faces)
        lo=(x*size-(halo+1)*spacing-radius,y*size-(halo+1)*spacing-radius)
        hi=((x+1)*size+(halo+1)*spacing+radius,(y+1)*size+(halo+1)*spacing+radius)
        local_solids=sorted((o for o in solids if all(o["min"][i]<hi[i] and o["max"][i]>lo[i] for i in (0,1))),key=lambda o:(o["min"],o["max"]))
        fingerprint=digest([settings_hash,faces,local_solids])
        saved=old.get(key)
        if saved and saved.get("source_hash")==fingerprint and saved.get("mesh_hash")==digest(saved.get("mesh")):
            mesh=saved["mesh"];reused.append(key)
        else:
            verts=[];triangles=[];index={}
            for face in faces:
                row=[]
                for p in face:
                    if p not in index:index[p]=len(verts);verts.append(p)
                    row.append(index[p])
                if len(set(row))==3:triangles.append(tuple(row))
            if not triangles:continue
            mesh=generate_collision({"schema":1,"vertices":verts,"triangles":triangles,"spacing":spacing,"agent":agent,"solid_obstacles":local_solids},
                grid_origin=(0.,0.),window=(x*tile_cells-halo,y*tile_cells-halo,(x+1)*tile_cells+halo,(y+1)*tile_cells+halo))
            rebuilt.append(key)
        tiles[key]={"source_hash":fingerprint,"mesh_hash":digest(mesh),"mesh":mesh}
    result=assemble(tiles,size)
    cache={"schema":1,"settings_hash":settings_hash,"settings":settings,"tiles":tiles}
    return {"mesh":result,"cache":cache,"rebuilt":rebuilt,"reused":reused,"removed":sorted(set(old)-set(tiles))}

def assemble(tiles,size):
    """Crop halo meshes by core ownership, verify cross-seam edges in both halos."""
    def coord(p):return tuple(round(float(v),7) for v in p)
    def tri_key(vs,t):
        return tuple(sorted(coord(vs[i]) for i in t))
    def owner(key):
        return tile_key(math.floor(sum(p[0] for p in key)/3/size),math.floor(sum(p[1] for p in key)/3/size))
    evidence={};step_evidence=defaultdict(set);step_rows={};core={};issues=[]
    for key,entry in sorted(tiles.items()):
        m=entry["mesh"];vs=m["vertices"];ts=m["triangles"]
        report=topology(vs,ts)
        keys=[tri_key(vs,t) for t in ts]
        if len(set(keys))!=len(keys):raise ValueError("duplicate geometry in halo")
        evidence[key]={tuple(sorted((keys[i],keys[j]))) for i,row in enumerate(report["neighbors"]) for j in row if j>=0}
        layer_values=m.get("triangle_layers")
        if layer_values is not None and len(layer_values)!=len(ts):raise ValueError("invalid halo layer metadata")
        for i,t in enumerate(ts):
            k=keys[i]
            if owner(k)!=key:continue
            if k in core:raise ValueError("duplicate core triangle")
            core[k]=(tuple(coord(vs[v]) for v in t),layer_values[i] if layer_values is not None else 0)
        for link in m.get("links",[]):
            a,b=keys[link["from"]],keys[link["to"]]
            pair=tuple(sorted((a,b)));step_evidence[pair].add(key)
            step_rows[pair]=link
    vertices=[];triangles=[];layers=[];owners=[];mapping={};index={}
    if len(core)>2000000:raise ValueError("assembled triangle limit; partition world")
    for k,(t,layer) in sorted(core.items()):
        row=[]
        for p in t:
            if p not in index:index[p]=len(vertices);vertices.append(p)
            row.append(index[p])
        mapping[k]=len(triangles);triangles.append(tuple(row));layers.append(layer);owners.append(owner(k))
    report=topology(vertices,triangles);keys=list(sorted(core));seams=0
    for i,row in enumerate(report["neighbors"]):
        for j in row:
            if j<=i or owners[i]==owners[j]:continue
            pair=tuple(sorted((keys[i],keys[j])))
            if not all(pair in evidence.get(k,set()) for k in (owners[i],owners[j])):
                raise ValueError("cross-tile edge lacks reciprocal halo evidence")
            seams+=1
    links=[]
    for pair,seen in sorted(step_evidence.items()):
        a,b=pair
        if a not in mapping or b not in mapping:continue
        required={owner(a),owner(b)}
        if not required<=seen:
            issues.append({"code":"unconfirmed-step-seam","tiles":sorted(required)});continue
        row=step_rows[pair]
        if not row.get("bidirectional") or not row.get("clearance_checked"):continue
        links.append({**row,"id":"step:"+digest(pair)[:24],"from":mapping[a],"to":mapping[b]})
    return {"schema":1,"vertices":vertices,"triangles":triangles,**report,"links":links,
            "triangle_layers":layers,"triangle_tiles":owners,"seam_edges":seams,"issues":issues,
            "scope":"portable tiled collision AutoNav with reciprocal halo seam verification"}

def load(path,limit=256*1024*1024):
    """Bounded project/cache JSON reader; the quest loader's 8MB cap is too small."""
    from pathlib import Path
    p=Path(path)
    if p.stat().st_size>limit:raise ValueError("navigation JSON exceeds input budget")
    with p.open(encoding="utf-8") as stream:return json.load(stream)
