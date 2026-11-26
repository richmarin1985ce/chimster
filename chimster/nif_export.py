"""Optional PyFFI-backed legacy NIF geometry export. No third-party code bundled."""
from pathlib import Path
from math import sqrt,isfinite
from .lod import validate_mesh
from .flora import cross
import io

def backend():
    # PyFFI 2.2.3 uses time.clock, removed in Python 3.8.
    import time
    if not hasattr(time,"clock"):time.clock=time.perf_counter
    from pyffi.formats.nif import NifFormat
    return NifFormat

def export_legacy(mesh,path,game="morrowind",scale=1.0,textures=None):
    """NiNode/NiTriShape with optional legacy base texture and alpha test; no collision or wind.
    Reopens with same library before publishing. Not a game-runtime certification."""
    validate_mesh(mesh)
    if game not in {"morrowind","openmw"}:raise ValueError("only legacy 4.0.0.2 enabled")
    if not isfinite(scale) or scale<=0:raise ValueError("invalid scale")
    path=Path(path)
    if path.suffix.lower()!=".nif":raise ValueError("expected NIF")
    if path.exists():raise FileExistsError(path)
    textures=textures or {}
    if set(textures)-{m for _,m in mesh.faces}:raise ValueError("unknown material")
    for mat,texture in textures.items():
        parts=texture.replace("\\","/").split("/")
        if not texture.lower().endswith(".dds") or parts[0].casefold()!="textures" or any(p in ("",".","..") for p in parts) or ":" in texture:raise ValueError("texture must be a relative textures/*.dds path")
    N=backend();data=N.Data(version=0x04000002)
    root=N.NiNode();root.name=b"Chimster Root";root.flags=14;root.scale=1
    root.rotation.set_identity()
    data.roots=[root]
    count=0
    for mat in sorted({m for _,m in mesh.faces}):
        faces=[f for f,m in mesh.faces if m==mat]
        ids=sorted({i for f in faces for i in f});mapping={j:i for i,j in enumerate(ids)}
        if len(ids)>65535 or len(faces)>65535:raise ValueError("legacy shape exceeds 16-bit limits")
        shape=N.NiTriShape();shape.name=mat.encode("ascii");shape.flags=14;shape.scale=1;shape.rotation.set_identity()
        geom=N.NiTriShapeData();shape.data=geom;root.add_child(shape)
        geom.num_vertices=len(ids);geom.has_vertices=True;geom.vertices.update_size()
        geom.has_normals=True;geom.normals.update_size()
        geom.num_uv_sets=1;geom.has_uv=True;geom.uv_sets.update_size()
        normals=[[0.,0.,0.] for _ in ids]
        verts=[mesh.vertices[j] for j in ids];tris=[tuple(mapping[j] for j in f) for f in faces]
        for a,b,c in tris:
            normal=cross(tuple(verts[b][i]-verts[a][i] for i in range(3)),tuple(verts[c][i]-verts[a][i] for i in range(3)))
            for j in (a,b,c):
                for i in range(3):normals[j][i]+=normal[i]
        for i,j in enumerate(ids):
            p=geom.vertices[i];p.x,p.y,p.z=(v*scale for v in verts[i])
            q=geom.normals[i];length=sqrt(sum(v*v for v in normals[i]))
            q.x,q.y,q.z=(tuple(v/length for v in normals[i]) if length else (0,0,1))
            uv=geom.uv_sets[0][i];uv.u,uv.v=mesh.uv[j][0],1-mesh.uv[j][1]
        geom.set_triangles(tris);geom.update_center_radius();count+=len(tris)
        if mat in textures:
            tex=N.NiSourceTexture();tex.use_external=True;tex.file_name=textures[mat].replace("/","\\").encode("ascii")
            prop=N.NiTexturingProperty();prop.texture_count=7;prop.has_base_texture=True;prop.base_texture.source=tex
            shape.add_property(prop)
            material=N.NiMaterialProperty()
            material.ambient_color.r=material.ambient_color.g=material.ambient_color.b=1.0
            material.diffuse_color.r=material.diffuse_color.g=material.diffuse_color.b=1.0
            material.alpha=1.0;shape.add_property(material)
            if mat.endswith("__cutout"):
                alpha=N.NiAlphaProperty();alpha.flags=0x1200;alpha.threshold=128;shape.add_property(alpha)
    stream=io.BytesIO();data.write(stream);raw=stream.getvalue()
    check=N.Data();check.read(io.BytesIO(raw))
    actual=sum(len(c.data.get_triangles()) for r in check.roots for c in r.children if isinstance(c,N.NiTriShape))
    if actual!=count or check.version!=0x04000002:raise ValueError("NIF round trip failed")
    for r in check.roots:
        for c in r.children:
            if c.name.decode("ascii") in textures:
                expected=textures[c.name.decode("ascii")].replace("/","\\").encode("ascii")
                if not any(isinstance(p,N.NiTexturingProperty) and p.has_base_texture and p.base_texture.source.file_name==expected for p in c.properties):
                    raise ValueError("texture roundtrip failed")
    with path.open("xb") as f:f.write(raw)
    return {"path":str(path),"triangles":count,"version":"4.0.0.2","status":"PyFFI geometry/optional texture round trip; no game smoke test"}

def export_billboard(recipe,root,size=128,views=2,scale=1.0):
    from .flora import generate
    from .lod import atlas_billboard
    from .lod_assets import write_dds
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    mesh,rgba,side,layout=atlas_billboard(generate(recipe),views,size)
    # Bake UV uses top-left; legacy exporter takes OBJ-like bottom-left.
    mesh.uv=[(u,1-v) for u,v in mesh.uv]
    # Legacy billboard needs both sides. Duplicate reversed triangles with
    # separate vertices so normals on opposite sides do not cancel.
    n=len(mesh.vertices);mesh.vertices.extend(mesh.vertices[:]);mesh.uv.extend(mesh.uv[:])
    mesh.faces.extend([((c+n,b+n,a+n),mat) for (a,b,c),mat in mesh.faces[:]])
    tex=root/"textures"/"chimster"/"tree_atlas.dds"
    nif=root/"meshes"/"chimster"/"tree_billboard.nif"
    tex.parent.mkdir(parents=True);nif.parent.mkdir(parents=True)
    write_dds(tex,side,side,rgba)
    result=export_legacy(mesh,nif,scale=scale,textures={"tree_atlas__cutout":"textures/chimster/tree_atlas.dds"})
    return {**result,"texture":str(tex),"atlas_size":side,"views":views}
