"""Explicit, local, game-specific compiler profiles; discovery never executes tools."""
from pathlib import Path
import json
import shutil
from .papyrus_build import family, digest, compiler_options, build
from .papyrus_batch import batch
from .integrations import executable, directory, file

def discover(game,install=None):
    target,_,_=family(game)
    root=directory(install) if install else None
    candidates=[]
    def add(kind,p):
        if p and Path(p).is_file():
            p=str(Path(p).resolve())
            if (kind,p) not in candidates:candidates.append((kind,p))
    for backend,aliases in (("ck",("PapyrusCompiler.exe",)),("caprica",("caprica","Caprica.exe")),("champollion",("champollion","Champollion.exe"))):
        for alias in aliases:
            if root:
                for folder in ("","Papyrus Compiler","Tools/Papyrus Compiler","Tools"):add(backend,root/folder/alias)
            add(backend,shutil.which(alias))
    roots=[];flags=[]
    if root:
        for folder in ("Data/Scripts/Source","Data/Source/Scripts","Data/Scripts/Source/Base","Data/Scripts/Source/User"):
            p=root/folder
            if p.is_dir():
                roots.append(str(p.resolve()))
                for flag in sorted(p.glob("*.flg")):
                    if flag.is_file():flags.append(str(flag.resolve()))
    return {"game":game,"family":target,"compilers":[{"backend":k,"path":p} for k,p in candidates],
            "source_roots":roots,"flags":list(dict.fromkeys(flags)),
            "scope":"candidate paths only; select and pin explicitly; no version or engine validation"}

def create(path,game,backend,compiler,flags,imports,*,options=None):
    switches=compiler_options(game,backend,**(options or {}))
    binary=executable(compiler);flag=file(flags,{".flg"})
    roots=list(dict.fromkeys(str(directory(p)) for p in imports))
    profile={"schema":1,"game":game,"backend":backend,"compiler":binary,
             "compiler_sha256":digest(binary),"flags":str(flag),"flags_sha256":digest(flag),
             "imports":roots,"options":options or {},"switches":switches}
    with Path(path).open("x",encoding="utf-8") as stream:json.dump(profile,stream,indent=2)
    return profile

def load(path):
    p=Path(path)
    if p.stat().st_size>65536:raise ValueError("compiler profile too large")
    cfg=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(cfg,dict) or cfg.get("schema")!=1:raise ValueError("invalid compiler profile")
    if not isinstance(cfg.get("imports"),list) or not all(isinstance(p,str) for p in cfg["imports"]):
        raise ValueError("invalid import directories")
    if not isinstance(cfg.get("options"),dict) or any(type(v) is not bool for v in cfg["options"].values()):
        raise ValueError("invalid compiler options")
    if compiler_options(cfg["game"],cfg["backend"],**cfg["options"])!=cfg["switches"]:raise ValueError("options changed")
    for key in ("compiler","flags"):
        resolved=executable(cfg[key]) if key=="compiler" else str(file(cfg[key],{".flg"}))
        if resolved!=cfg[key] or digest(resolved)!=cfg[key+"_sha256"]:raise ValueError("pinned "+key+" changed; create new profile")
    for root in cfg["imports"]:directory(root)
    return cfg

def configured_build(profile,source,output,*,project=False,execute=False,reuse=None,timeout=120):
    cfg=load(profile)
    args=(cfg["game"],cfg["backend"],cfg["compiler"],source,cfg["flags"],cfg["imports"],output)
    if project:return batch(*args,execute=execute,timeout=timeout,options=cfg["options"],reuse=reuse)
    if reuse:raise ValueError("reuse is project-only")
    return build(*args,execute=execute,timeout=timeout,options=cfg["options"])
