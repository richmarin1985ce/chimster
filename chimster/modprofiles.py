"""Isolated local mod ZIP installation and atomic profile snapshots."""
from pathlib import Path, PurePosixPath
import json, os, re, shutil, stat, tempfile, zipfile

def safe_id(name):
    if not isinstance(name,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}",name): raise ValueError("invalid profile/mod identifier")
    return name

def save_profile(root,name,game,mods,plugins):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    name=safe_id(name)
    if len({safe_id(m).casefold() for m in mods})!=len(mods): raise ValueError("duplicate mods")
    from .loadorder import plugin_name
    if len({plugin_name(p) for p in plugins})!=len(plugins): raise ValueError("duplicate plugins")
    dest=root/(name+".json")
    fd,tmp=tempfile.mkstemp(prefix=".profile-",dir=root)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump({"game":game,"mods":mods,"plugins":plugins},f,indent=2);f.write("\n")
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,dest)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    return dest

def install_zip(root,archive,mod_id,*,max_bytes=2*1024**3,max_files=50000):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    dest=root/safe_id(mod_id)
    if dest.exists() or dest.is_symlink(): raise FileExistsError(dest)
    stage=Path(tempfile.mkdtemp(prefix=".install-",dir=root))
    try:
        with zipfile.ZipFile(archive) as z:
            entries=z.infolist()
            if len(entries)>max_files or sum(i.file_size for i in entries)>max_bytes: raise ValueError("archive exceeds configured limits")
            seen=set()
            for i in entries:
                name=i.filename
                p=PurePosixPath(name)
                mode=(i.external_attr>>16)&0xffff
                if not p.parts or p.is_absolute() or ".." in p.parts or "\\" in name or ":" in name or any(part.endswith((".", " ")) or part.split(".")[0].upper() in {"CON","PRN","AUX","NUL",*(f"COM{x}" for x in range(1,10)),*(f"LPT{x}" for x in range(1,10))} for part in p.parts) or stat.S_ISLNK(mode):
                    raise ValueError("unsafe archive entry: "+name)
                key=p.as_posix().casefold()
                if key in seen: raise ValueError("duplicate archive entry")
                seen.add(key)
                target=stage.joinpath(*p.parts)
                if i.is_dir(): target.mkdir(parents=True,exist_ok=True)
                else:
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with z.open(i) as src,target.open("xb") as out: shutil.copyfileobj(src,out)
        if dest.exists() or dest.is_symlink(): raise FileExistsError(dest)
        stage.rename(dest)
        return dest
    finally:
        if stage.exists(): shutil.rmtree(stage)
