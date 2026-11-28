"""Staged native LOD tool handoff and output auditing (no fake runtime NIFs)."""
from pathlib import Path
import re
import hashlib
import json
from .xedit import Workspace
from .lod_tools import tool_plan,run_tool
from .world_lod_metadata import world_bounds
from .loadorder import fingerprint

GAME={"new-vegas":"newvegas","fallout3":"fallout3","oblivion":"oblivion","skyrim":"skyrim","skyrim-se":"skyrimse","fallout4":"fallout4"}
def world_name(browser,world):
    row=browser.worlds.get(world)
    if not row:raise ValueError("Select an exterior worldspace")
    name=row.get("editor_id","")
    if not re.fullmatch(r"[A-Za-z0-9_ -]{1,128}",name):raise ValueError("Unsafe or missing worldspace EditorID")
    return name

def prepare(browser,world,workspace,executable):
    name=world_name(browser,world)
    if GAME.get(browser.profile)!=workspace.game:raise ValueError("Workspace game does not match browser")
    paths=workspace.paths()
    # Require identical staged copies of the browser load order, including exported drafts.
    sources=getattr(browser,"source_paths",None)
    hashes=getattr(browser,"source_hashes",None)
    if not sources or not hashes:raise ValueError("Export staged edits and reopen their ESP before native generation")
    by_name={}
    for p in paths["data"].iterdir():
        if p.is_file() and p.suffix.lower() in (".esm",".esp",".esl"):
            k=p.name.casefold()
            if k in by_name:raise ValueError("Duplicate staged plugin name")
            by_name[k]=p
    expected=[p.name.casefold() for p in sources]
    actual=[]
    for line in paths["plugins"].read_text(encoding="utf-8-sig").splitlines():
        line=line.strip()
        if line and not line.startswith("#"):actual.append(line.lstrip("*").casefold())
    # Some games omit implicit masters from plugins.txt. Do not guess.
    if actual!=expected:raise ValueError("Staged plugins.txt must list the exact browser load order including masters")
    for path,digest in zip(sources,hashes):
        staged=by_name.get(path.name.casefold())
        if staged is None or fingerprint(staged)!=digest or fingerprint(path)!=digest:
            raise ValueError("Staged or source plugin changed: "+path.name)
    ext=".dlodsettings" if workspace.game in ("newvegas","fallout3") else ".lod"
    setting="LODSettings/"+name+ext
    candidates=[p for p in paths["data"].rglob("*") if p.is_file() and p.relative_to(paths["data"]).as_posix().casefold()==setting.casefold()]
    if not candidates:
        # Look only in explicit staged archives; registration still requires review.
        from .archive_reader import directory
        from .compatibility_asset_lookup import normalize
        for p in paths["data"].iterdir():
            if p.suffix.casefold() not in (".bsa",".ba2"):continue
            try:
                if normalize(setting) in directory(p):candidates.append(p)
            except (OSError,ValueError):continue
    plan=tool_plan(workspace,"xlodgen",executable)
    return {**plan,"world":name,"game":workspace.game,"settings":setting,
            "settings_sources":[str(p) for p in candidates],"settings_missing":not candidates,
            "world_bounds":world_bounds(r["grid"] for r in browser.cells[world] if "grid" in r),
            "source_plugins":expected,"source_hashes":list(hashes),
            "notes":"Select this world in xLODGen. Generate missing LODSettings with the external tool/GECK. Review native outputs before installing."}

def launch(browser,world,workspace,executable):
    plan=prepare(browser,world,workspace,executable)
    if plan["settings_missing"]:raise ValueError("Missing LODSettings; prepare with GECK or xLODGen before generation")
    return run_tool(workspace,"xlodgen",executable),plan

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
