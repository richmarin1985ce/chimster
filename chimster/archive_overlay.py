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
