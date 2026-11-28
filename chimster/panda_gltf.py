"""Read-only, embedded GLB preview through the upstream panda3d-gltf loader."""
from pathlib import Path
import json,struct

def validate_glb(path):
    p=Path(path).resolve(strict=True)
    if p.suffix.lower()!=".glb" or not 20<=p.stat().st_size<=64*1024*1024:
        raise ValueError("Expected a self-contained GLB, at most 64 MiB")
    with p.open("rb") as f:
        magic,version,total,size,kind=struct.unpack("<4sIIII",f.read(20))
        if magic!=b"glTF" or version!=2 or total!=p.stat().st_size or kind!=0x4e4f534a or size>8*1024*1024 or size>total-20:
            raise ValueError("Invalid GLB header")
        data=json.loads(f.read(size))
    if not isinstance(data,dict) or data.get("asset",{}).get("version")!="2.0":
        raise ValueError("Expected glTF 2.0")
    stack=[data]
    while stack:
        value=stack.pop()
        if isinstance(value,dict):
            if "uri" in value:raise ValueError("External and data URI resources are not supported in preview")
            stack.extend(value.values())
        elif isinstance(value,list):stack.extend(value)
    return p

def load_preview(path):
    from gltf import load_model,GltfSettings
    from panda3d.core import NodePath,Filename
    p=validate_glb(path)
    return NodePath(load_model(Filename.from_os_specific(str(p)).get_fullpath(),GltfSettings(skip_animations=True)))
