"""Optional Fallout 4 native physics reader via a user-installed PyNifly backend.

Requires the CollisionShape/body_index API. No render-mesh fallback.
The narrow first adapter accepts only one static root body and identity root/body
transform, avoiding unresolved body-vs-node transform conventions.
"""
import math
from pathlib import Path
from .navmesh import point,num

def mesh_from_body(shapes,body_id,unit_scale):
    scale=num(unit_scale,1e-6,1e5)
    if type(body_id) is not int or not 0<=body_id<0xffffffff:raise ValueError("invalid native body ID")
    if len(shapes)!=1 or shapes[0].body_index!=body_id:raise ValueError("requires one matching decoded physics body")
    root=shapes[0];physics=root.physics
    if physics is None or physics.is_dynamic or physics.trigger or physics.motion_id!=0x7fffffff:
        raise ValueError("requires static non-trigger native body")
    ident=((1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
    def matrix(tf,root=False):
        if tf is None:return lambda p:p
        r=tuple(tuple(float(v) for v in row) for row in tf.rotation)
        t=point(tf.position);s=num(tf.scale,1e-6,1e4)
        if len(r)!=3 or any(len(row)!=3 or not all(math.isfinite(x) for x in row) for row in r):raise ValueError("invalid collision rotation")
        if any(abs(sum(r[i][k]*r[j][k] for k in range(3))-(i==j))>1e-5 for i in range(3) for j in range(3)):raise ValueError("nonrigid collision rotation")
        det=r[0][0]*(r[1][1]*r[2][2]-r[1][2]*r[2][1])-r[0][1]*(r[1][0]*r[2][2]-r[1][2]*r[2][0])+r[0][2]*(r[1][0]*r[2][1]-r[1][1]*r[2][0])
        if abs(det-1)>1e-5:raise ValueError("reflected collision rotation")
        if root and (math.dist(t,(0,0,0))>1e-6 or abs(s-1)>1e-6 or any(abs(r[i][j]-ident[i][j])>1e-6 for i in range(3) for j in range(3))):
            raise ValueError("nonidentity root body transform requires separate placement review")
        return lambda p:tuple(t[i]+s*sum(r[i][j]*p[j] for j in range(3)) for i in range(3))
    verts=[];tris=[];seen=set();count=0
    def walk(shape,parent,depth):
        nonlocal count
        if depth>32 or id(shape) in seen or count>=4096:raise ValueError("collision graph limit or cycle")
        seen.add(id(shape));count+=1
        transform=matrix(shape.transform,depth==0)
        def apply(p):return parent(transform(p))
        if shape.shape_type=="compound":
            if not shape.children:raise ValueError("empty compound")
            for c in shape.children:walk(c,apply,depth+1)
        elif shape.shape_type in ("polytope","compressed_mesh"):
            if shape.children or getattr(shape,"capsule_ends",None) is not None:raise ValueError("unsupported collision primitive")
            if not shape.verts or not shape.faces or len(verts)+len(shape.verts)>500000 or len(tris)+len(shape.faces)>500000:
                raise ValueError("empty or oversized collision mesh")
            offset=len(verts)
            verts.extend(point(tuple(v*scale for v in apply(point(p)))) for p in shape.verts)
            for f in shape.faces:
                if len(f)!=3 or len(set(f))!=3 or any(type(i) is not int or not 0<=i<len(shape.verts) for i in f):raise ValueError("invalid native collision face")
                tris.append(tuple(offset+i for i in f))
        else:raise ValueError("unsupported native collision shape: "+str(shape.shape_type))
        seen.remove(id(shape))
    walk(root,lambda p:p,0)
    return {"vertices":verts,"triangles":tris}

def extract(path,unit_scale):
    p=Path(path).resolve(strict=True)
    if p.suffix.lower()!=".nif" or p.stat().st_size>128*1024*1024:raise ValueError("expected bounded NIF")
    try:
        from io_scene_nifly.pyn.pynifly import NifFile
        from io_scene_nifly.pyn.bhk_autounpack import parse_bytes,unsupported_shapes
    except ImportError as exc:raise RuntimeError("install a compatible local PyNifly backend first") from exc
    nif=NifFile(str(p))
    if nif.game!="FO4":raise ValueError("expected Fallout 4 NIF")
    root=nif.root;coll=root.collision_object
    if not coll or coll.blockname!="bhkNPCollisionObject":raise ValueError("expected root native physics collision")
    # Explicitly reject a nonidentity node transform and other collision nodes.
    tf=root.transform
    rotation=tuple(tuple(float(v) for v in row) for row in tf.rotation)
    if any(abs(v)>1e-6 for v in tf.translation) or abs(tf.scale-1)>1e-6 or any(abs(rotation[i][j]-(i==j))>1e-6 for i in range(3) for j in range(3)):
        raise ValueError("nonidentity NIF root transform")
    if any(node.id!=root.id and node.collision_object for node in nif.nodes.values()):
        raise ValueError("multiple collision nodes require placement review")
    ps=coll.physics_system
    raw=ps.data if ps else b""
    if not raw or len(raw)>128*1024*1024 or unsupported_shapes(raw):raise ValueError("missing or unsupported native physics data")
    return mesh_from_body(parse_bytes(raw),coll.body_id,unit_scale)
