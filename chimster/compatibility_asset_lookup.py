"""Read-only asset lookup across caller-ordered archive and loose-file layers."""
def normalize(path):
    if not isinstance(path,str) or not path or "\0" in path:raise ValueError("Invalid asset path")
    path=path.replace("\\","/")
    parts=path.split("/")
    if any(p in ("",".","..") or ":" in p for p in parts):raise ValueError("Unsafe asset path")
    return "/".join(parts).casefold()

def index(layers):
    """Layers ordered lowest to highest precedence; each contains (path, locator)."""
    result={}
    for name,entries in layers:
        seen=set()
        for path,locator in entries:
            key=normalize(path)
            if key in seen:raise ValueError("Ambiguous asset within layer")
            seen.add(key)
            result.setdefault(key,[]).append({"layer":name,"path":path,"locator":locator})
    return result

def resolve(catalog,path):
    candidates=catalog.get(normalize(path),[])
    return {"winner":candidates[-1] if candidates else None,"shadowed":candidates[:-1]}
