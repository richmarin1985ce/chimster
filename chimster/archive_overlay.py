"""Explicit user-ordered asset layers; not a simulation of engine loading.
Classic Fallout archive precedence depends on configuration:
https://geckwiki.com/index.php/BSA_Files
"""
from pathlib import Path
from .archive_reader import directory
from .compatibility_asset_lookup import index

def build(sources):
    layers=[]
    for source in sources:
        path=Path(source)
        if path.is_dir():
            entries=[(p.relative_to(path).as_posix(),("loose",str(p))) for p in path.rglob("*") if p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(path.resolve())]
        else:
            entries=[(name,("archive",str(path),name)) for name in directory(path)]
        layers.append((str(path),entries))
    return index(layers)


def build_profile(profile,plugins,archives,*,config=None,loose=(),loose_policy=None):
    """Build a preview from explicit low-to-high plugin order and INI registration."""
    from .archive_precedence import plan
    from .archive_config import read
    configuration=read(profile,config) if config is not None else {"base_archives":[],"settings":{}}
    ordering=plan(profile,plugins,archives,base_archives=configuration["base_archives"],
                  loose=loose,loose_policy=loose_policy)
    ordering["settings"]=configuration["settings"]
    ordering["catalog"]=build(ordering["layers"])
    return ordering

def conflicts(overlay,query="",limit=500):
    """Return bounded conflict rows with full provenance for each selected asset."""
    from .compatibility_asset_lookup import resolve
    if not isinstance(limit,int) or not 1<=limit<=10000:raise ValueError("Invalid result limit")
    catalog=overlay["catalog"]
    keys=sorted(k for k,v in catalog.items() if len(v)>1 and query.casefold() in k)
    return {"total":len(keys),"rows":[{"asset":k,**resolve(catalog,k)} for k in keys[:limit]],
            "engine_verified":False}
