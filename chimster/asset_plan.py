"""Review-only static asset/LOD proposals. No plugin writes or NIF conversion."""
from pathlib import Path, PurePosixPath
from hashlib import sha256
import re
from .xedit import MODES

STATIC_PROFILES={"oblivion","fallout3","newvegas","skyrim","skyrimse","skyrimvr","fallout4","fallout4vr","enderal","enderalse"}
def asset_file(root, relative, folder, extension):
    if not isinstance(relative,str) or "\\" in relative or ":" in relative:
        raise ValueError("use relative forward-slash paths")
    p=PurePosixPath(relative)
    if p.is_absolute() or ".." in p.parts or len(p.parts)<2 or p.parts[0].lower()!=folder or p.suffix.lower()!=extension:
        raise ValueError("unexpected asset path: "+relative)
    real=root.joinpath(*p.parts).resolve(strict=True)
    if not real.is_file() or not real.is_relative_to(root):
        raise ValueError("asset outside staged Data")
    return {"path":p.as_posix(),"sha256":sha256(real.read_bytes()).hexdigest()}

def static_proposal(game, staged_data, assets):
    if game not in STATIC_PROFILES:
        raise ValueError("static proposal adapter not enabled for this game")
    root=Path(staged_data).resolve(strict=True)
    if not root.is_dir(): raise ValueError("Data must be a directory")
    proposed=[]; groups={}; seen=set()
    for a in assets:
        edid=a["editor_id"]
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,127}",edid) or edid.casefold() in seen:
            raise ValueError("invalid or duplicate EditorID")
        seen.add(edid.casefold())
        model=asset_file(root,a["model"],"meshes",".nif")
        lod=[asset_file(root,p,"meshes",".nif") for p in a.get("object_lod",[])]
        if len({x["path"].casefold() for x in [model,*lod]})!=1+len(lod):
            raise ValueError("duplicate mesh paths")
        # Group only exact declared material compatibility, no atlas claims.
        for mat in a.get("materials",[]):
            mode=mat["alpha"]
            if mode not in {"opaque","cutout","blend"}: raise ValueError("unknown alpha mode")
            if not isinstance(mat["tiling"],bool): raise ValueError("tiling must be boolean")
            textures=tuple((role,asset_file(root,path,"textures",".dds")["sha256"]) for role,path in sorted(mat["textures"].items()))
            if not textures: raise ValueError("material needs textures")
            key=(mat["shader"],mode,mat["tiling"],textures)
            groups.setdefault(key,set()).add(edid)
        proposed.append({"operation":"propose_new_static","signature":"STAT","editor_id":edid,
                         "model":model,"object_lod_candidates":lod,"native_tree_lod":False})
    return {"game":game,"records":proposed,"material_groups":[
        {"shader":k[0],"alpha":k[1],"tiling":k[2],"texture_hashes":dict(k[3]),"editor_ids":sorted(v)}
        for k,v in groups.items()],"approval_required":True,"writes_plugin":False,
        "warning":"File existence and hashes only; NIF compatibility, collision, record schema, LOD slot assignments and EditorID collisions with existing records need xEdit/game validation."}
