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

def audit(output,world,game):
    root=Path(output).resolve(strict=True)
    if not root.is_dir():raise ValueError("Expected LOD output folder")
    if not re.fullmatch(r"[A-Za-z0-9_ -]{1,128}",world):raise ValueError("Invalid worldspace")
    expected=world.casefold()
    rows=[];issues=[];seen=set()
    for p in sorted(root.rglob("*")):
        if p.is_symlink():raise ValueError("Symlink in LOD output")
        if not p.is_file():continue
        rel=p.relative_to(root).as_posix();low=rel.casefold()
        if low in seen:raise ValueError("Case-colliding output paths")
        seen.add(low)
        if expected not in low.split("/") and not p.name.casefold().startswith(expected+"."):continue
        ext=p.suffix.lower()
        if ext not in (".nif",".btr",".bto",".dds",".dtl",".lod",".dlodsettings",".btt"):continue
        if len(rows)>=100000:raise ValueError("LOD output file limit")
        if p.stat().st_size==0:issues.append("Empty: "+rel)
        with p.open("rb") as f:magic=f.read(64)
        if ext==".dds" and (not magic.startswith(b"DDS ") or p.stat().st_size<128):issues.append("Invalid DDS: "+rel)
        if ext in (".nif",".btr",".bto") and not magic.startswith((b"Gamebryo File Format",b"NetImmerse File Format")):issues.append("Unexpected NIF header: "+rel)
        kind="other";level=None
        m=re.search(r"\.level(4|8|16|32)\.",p.name,re.I)
        if m:level=int(m.group(1))
        if ext==".nif" and "/blocks/" in low:kind="object"
        elif ext==".nif" and "/landscape/lod/" in "/"+low:kind="terrain"
        elif ext==".btr":kind="terrain"
        elif ext==".bto":kind="object"
        elif ext in (".dtl",".btt"):kind="tree"
        elif ext==".dds":kind="texture"
        elif ext in (".lod",".dlodsettings"):kind="settings"
        rows.append({"file":rel,"kind":kind,"level":level,"bytes":p.stat().st_size,"sha256":fingerprint(p)})
    if not rows:issues.append("No matching worldspace LOD output")
    if not any(r["kind"]=="terrain" for r in rows):issues.append("No terrain meshes found")
    if not any(r["kind"]=="texture" for r in rows):issues.append("No textures found")
    return {"world":world,"game":game,"files":rows,"issues":issues,"valid_headers":not issues,
            "engine_verified":False,"scope":"Header and inventory checks only; inspect texture links, geometry and game runtime."}
