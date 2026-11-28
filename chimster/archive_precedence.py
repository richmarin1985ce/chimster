"""Conservative archive association planner, not a verified engine emulator."""
from pathlib import Path

CLASSIC={"oblivion","fallout3","new-vegas","skyrim","skyrim-se","skyrim-vr"}
MODERN={"fallout4","fallout4-vr"}

def plan(profile,plugins,archives,*,base_archives=(),loose=(),loose_policy=None):
    if profile not in CLASSIC|MODERN|{"morrowind"}:raise ValueError("Unsupported profile")
    if loose_policy not in ("first","last","exclude"):raise ValueError("Explicit loose-file policy required")
    paths={}
    for item in archives:
        p=Path(item);key=p.name.casefold()
        if key in paths:raise ValueError("Ambiguous archive basename: "+key)
        paths[key]=str(p)
    layers=[];used=set();associations=[]
    def add(key,owner):
        if key not in paths:raise ValueError("Configured archive missing: "+key)
        if key in used:return
        used.add(key);layers.append(paths[key]);associations.append({"archive":paths[key],"owner":owner})
    for item in base_archives:add(Path(item).name.casefold(),"configured base")
    seen=set()
    for item in plugins:
        p=Path(item)
        if p.suffix.lower() not in (".esm",".esp",".esl"):raise ValueError("Invalid plugin name")
        stem=p.stem.casefold()
        if stem in seen:raise ValueError("Ambiguous plugin basename")
        seen.add(stem)
        if profile in MODERN:
            names=[stem+" - main.ba2",stem+" - textures.ba2"]
        elif profile in CLASSIC:
            names=[stem+".bsa"]
            if profile in {"skyrim-se","skyrim-vr"}:names.append(stem+" - textures.bsa")
        else:names=[] # Morrowind archives require explicit registration.
        for key in names:
            if key in paths:add(key,str(item))
    loose=list(map(str,loose))
    if loose_policy=="first":layers=loose+layers
    elif loose_policy=="last":layers+=loose
    return {"profile":profile,"layers":layers,"associations":associations,
            "unassociated":[paths[k] for k in sorted(paths.keys()-used)],
            "loose_policy":loose_policy,"engine_verified":False,
            "warnings":["Archive registration and invalidation settings must be supplied explicitly; association rules are provisional."]}
