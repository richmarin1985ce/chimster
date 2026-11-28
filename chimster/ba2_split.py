"""Split authorized mod assets into conventional Fallout 4 archive pairs."""
import os,tempfile
from pathlib import Path
from .archive_packaging import package_assets,package_textures
from .compatibility_asset_lookup import normalize
from .dds_texture import parse

def split(entries,limit=256*1024*1024):
    general=[];textures=[];seen=set();total=0
    for name,raw in entries:
        key=normalize(name)
        if key in seen or not isinstance(raw,bytes):raise ValueError("Duplicate or invalid asset")
        seen.add(key);total+=len(raw)+64+len(key.encode("ascii"))
        if total>limit:raise ValueError("Asset budget exceeded")
        if key.endswith(".dds"):
            parse(raw)
            textures.append((key,raw))
        else:
            general.append((key,raw))
    return general,textures

def package_pair(destination,stem,entries,*,version=1,compress=True,limit=256*1024*1024):
    root=Path(destination)
    if not root.is_dir() or not stem.strip() or any(c in stem for c in '/\\:') or stem in ('.','..'):
        raise ValueError("Invalid destination or mod name")
    general,textures=split(entries,limit)
    if not general and not textures:raise ValueError("No assets")
    plans=[(stem+" - Main.ba2",general,package_assets),(stem+" - Textures.ba2",textures,package_textures)]
    plans=[p for p in plans if p[1]]
    if any(os.path.lexists(root/name) for name,_,_ in plans):raise FileExistsError("Archive already exists")
    published=[];results=[]
    with tempfile.TemporaryDirectory(prefix=".chimster-",dir=root) as temp:
        for name,rows,writer in plans:
            result=writer(Path(temp)/name,rows,version=version,compress=compress,limit=limit)
            result["path"]=str(root/name);results.append(result)
        try:
            for name,_,_ in plans:
                source=Path(temp)/name;target=root/name
                os.link(source,target);published.append((source,target))
        except OSError:
            for source,target in reversed(published):
                if target.exists() and os.path.samestat(source.stat(),target.stat()):target.unlink()
            raise
    return {"archives":results,"general_members":len(general),"texture_members":len(textures),"retail_verified":False}
