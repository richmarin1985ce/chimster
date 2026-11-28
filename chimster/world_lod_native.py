"""Built-in native LOD output auditing and worldspace name handling."""
from pathlib import Path
import re
import hashlib
import json
from .loadorder import fingerprint

GAME={"new-vegas":"newvegas","fallout3":"fallout3","oblivion":"oblivion","skyrim":"skyrim","skyrim-se":"skyrimse","fallout4":"fallout4"}
def world_name(browser,world):
    row=browser.worlds.get(world)
    if not row:raise ValueError("Select an exterior worldspace")
    name=row.get("editor_id","")
    if not re.fullmatch(r"[A-Za-z0-9_ -]{1,128}",name):raise ValueError("Unsafe or missing worldspace EditorID")
    return name

def audit(output,world,game,deep=False):
    root=Path(output).resolve(strict=True)
    if not root.is_dir():raise ValueError("Expected LOD output folder")
    if not re.fullmatch(r"[A-Za-z0-9_ -]{1,128}",world):raise ValueError("Invalid worldspace")
    expected=world.casefold()
    rows=[];issues=[];seen=set();tes4_id=None
    if game=="oblivion" and (root/"manifest.json").is_file():
        manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
        if manifest.get("world","").casefold()==expected and type(manifest.get("formid"))==int:tes4_id=str(manifest["formid"])
    for p in sorted(root.rglob("*")):
        if p.is_symlink():raise ValueError("Symlink in LOD output")
        if not p.is_file():continue
        rel=p.relative_to(root).as_posix();low=rel.casefold()
        if low in seen:raise ValueError("Case-colliding output paths")
        seen.add(low)
        named=p.name.casefold()
        tes4=game=="oblivion" and (named.startswith(expected+"_") or (tes4_id is not None and named.startswith(tes4_id+".")))
        if expected not in low.split("/") and not named.startswith(expected+".") and not tes4:continue
        ext=p.suffix.lower()
        if ext not in (".nif",".btr",".bto",".dds",".dtl",".lod",".dlodsettings",".btt",".lst",".cmp"):continue
        if len(rows)>=100000:raise ValueError("LOD output file limit")
        if p.stat().st_size==0:issues.append("Empty: "+rel)
        with p.open("rb") as f:magic=f.read(64)
        if ext==".dds" and (not magic.startswith(b"DDS ") or p.stat().st_size<128):issues.append("Invalid DDS: "+rel)
        if ext in (".nif",".btr",".bto") and not magic.startswith((b"Gamebryo File Format",b"NetImmerse File Format")):issues.append("Unexpected NIF header: "+rel)
        kind="other";level=None
        m=re.search(r"\.(?:level)?(4|8|16|32)\.",p.name,re.I)
        if m:level=int(m.group(1))
        if ext==".nif" and "/blocks/" in low:kind="object"
        elif ext==".nif" and "/landscape/lod/" in "/"+low:kind="terrain"
        elif ext==".btr":kind="terrain"
        elif ext==".bto":kind="object"
        elif ext in (".dtl",".btt",".lst"):kind="tree"
        elif ext==".dds":kind="texture"
        elif game=="oblivion" and ext in (".lod",".cmp"):kind="placement"
        elif ext in (".lod",".dlodsettings"):kind="settings"
        info={}
        if deep:
            try:
                if p.stat().st_size>64*1024*1024:raise ValueError("File exceeds deep audit budget")
                raw=p.read_bytes()
                if ext==".dds":
                    from .lod_dds import decode
                    w,h,_=decode(raw);info={"width":w,"height":h}
                elif ext==".dlodsettings":
                    from .world_lod_metadata import read_fnv_settings
                    info=read_fnv_settings(raw)
                elif game=="oblivion" and ext in (".lod",".cmp"):
                    from .world_lod_oblivion_objects import decode_cell,decode_index
                    info={"references":sum(map(len,decode_cell(raw).values()))} if ext==".lod" else {"cells":len(decode_index(raw))}
                elif ext==".lod":
                    from .world_lod_metadata import read_skyrim_settings
                    info=read_skyrim_settings(raw)
                elif ext==".lst":
                    from .world_lod_tree_tiles import decode_types
                    info={"types":len(decode_types(raw))}
                elif ext==".btt":
                    from .world_lod_tree_tiles import decode_tile
                    groups=decode_tile(raw);info={"references":sum(map(len,groups.values())),"types":sorted(groups)}
                elif ext in (".btr",".bto") and game in ("skyrim","skyrimse","skyrim-se","fallout4"):
                    from .modern_lod_codec import inspect
                    info=inspect(raw,"skyrim-se" if game=="skyrimse" else game)
                elif ext==".nif" and game=="oblivion":
                    from .oblivion_lod_nif import inspect
                    info=inspect(raw)
                elif ext==".nif" and game in ("newvegas","new-vegas","fallout3"):
                    from .fnv_lod_nif import blocks,decode_geometry
                    geoms=[decode_geometry(b) for t,b in blocks(raw) if t=="NiTriShapeData"]
                    if not geoms:raise ValueError("No supported geometry")
                    info={"triangles":sum(len(g.faces) for g in geoms)}
            except (ValueError,TypeError,OSError,UnicodeError) as exc:issues.append("Deep audit "+rel+": "+str(exc))
        rows.append({"file":rel,"kind":kind,"level":level,"bytes":p.stat().st_size,"sha256":fingerprint(p),"details":info})
    if not rows:issues.append("No matching worldspace LOD output")
    if not any(r["kind"] in ("object","tree","placement") for r in rows):
        if not any(r["kind"]=="terrain" for r in rows):issues.append("No terrain meshes found")
        if not any(r["kind"]=="texture" for r in rows):issues.append("No textures found")
    return {"world":world,"game":game,"files":rows,"issues":issues,"valid_headers":not issues,
            "engine_verified":False,"scope":"Bounded internal binary inspection; engine behavior unverified." if deep else "Header and inventory checks only; inspect texture links, geometry and game runtime."}
