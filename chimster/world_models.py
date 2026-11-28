"""Optional static NIF geometry reader for user-supplied loose assets.

Uses the existing optional PyFFI backend. No archive extraction or materials.
Unsupported scene graphs fail closed; caller can render a proxy instead.
"""
from pathlib import Path
from math import isfinite
from .nif_export import backend
from .flora import Mesh
from .lod import validate_mesh


def resolve_model(root, model):
    root = Path(root).resolve(strict=True)
    parts = model.replace("\\","/").split("/")
    if parts[0].casefold() != "meshes":
        parts.insert(0,"meshes")
    if any(not p or p in (".","..") or ":" in p or "\0" in p for p in parts) or not parts[-1].casefold().endswith(".nif"):
        raise ValueError("Unsafe NIF model path")
    path = root
    for part in parts:
        matches = [p for p in path.iterdir() if p.name.casefold()==part.casefold()]
        if len(matches)!=1:
            raise ValueError("Missing or ambiguous loose model: "+model)
        path = matches[0].resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError("Model path escapes Data directory")
    if not path.is_file() or path.stat().st_size>64*1024*1024:
        raise ValueError("NIF file exceeds limits")
    return path


def read_static(path, units=128):
    N = backend()
    data = N.Data()
    with Path(path).open("rb") as stream:
        data.read(stream)
    if data.version not in (0x04000002,0x14020007):
        raise ValueError("Unsupported NIF version")
    mesh = Mesh()
    seen = set()
    def walk(node, transforms=(), depth=0):
        if depth>32 or id(node) in seen:
            raise ValueError("Unsupported shared or cyclic NIF scene graph")
        seen.add(id(node))
        if not isinstance(node,N.NiAVObject):
            raise ValueError("Unsupported NIF scene object")
        if getattr(node,"controller",None):
            raise ValueError("Animated NIF geometry unsupported")
        chain = (node.get_transform(),)+transforms
        if isinstance(node,N.NiNode):
            for child in node.children:
                if child is not None:walk(child,chain,depth+1)
        elif isinstance(node,N.NiTriBasedGeom):
            if getattr(node,"skin_instance",None) or node.data is None:
                raise ValueError("Skinned or missing geometry")
            geom = node.data
            vertices = list(geom.vertices)
            triangles = geom.get_triangles()
            if len(mesh.vertices)+len(vertices)>100000 or len(mesh.faces)+len(triangles)>100000:
                raise ValueError("NIF preview geometry budget exceeded")
            offset = len(mesh.vertices)
            uv = geom.uv_sets[0] if len(geom.uv_sets) else ()
            for i,v in enumerate(vertices):
                for matrix in chain:v = v*matrix
                point = tuple(float(x)/units for x in (v.x,v.y,v.z))
                if not all(isfinite(x) for x in point):
                    raise ValueError("Nonfinite NIF transform")
                mesh.vertices.append(point)
                mesh.uv.append((float(uv[i].u),1-float(uv[i].v)) if len(uv)>i else (0,0))
            for tri in triangles:
                if len(set(tri))==3:
                    mesh.faces.append((tuple(offset+i for i in tri),"native_nif"))
        else:
            raise ValueError("Unsupported NIF render object")
    for root in data.roots:walk(root)
    validate_mesh(mesh)
    return mesh


class LooseModels:
    def __init__(self, root):
        self.root = Path(root)
        self.cache = {}
    def __call__(self, model):
        key = model.replace("\\","/").casefold()
        if key not in self.cache:
            if len(self.cache)>=64:
                raise ValueError("Model cache limit reached")
            self.cache[key] = read_static(resolve_model(self.root,model))
        return self.cache[key]
