"""Local read-only installation discovery. Never launch or modify games."""
from pathlib import Path

GAMES={
 "morrowind":("Morrowind.exe","Morrowind.esm","Data Files"),
 "oblivion":("Oblivion.exe","Oblivion.esm","Data"),
 "fallout3":("Fallout3.exe","Fallout3.esm","Data"),
 "new-vegas":("FalloutNV.exe","FalloutNV.esm","Data"),
 "skyrim":("TESV.exe","Skyrim.esm","Data"),
 "skyrim-se":("SkyrimSE.exe","Skyrim.esm","Data"),
 "skyrim-vr":("SkyrimVR.exe","Skyrim.esm","Data"),
 "fallout4":("Fallout4.exe","Fallout4.esm","Data"),
 "fallout4-vr":("Fallout4VR.exe","Fallout4.esm","Data"),
}
def inspect(root,profile):
    root=Path(root).expanduser()
    exe,master,folder=GAMES[profile]
    def locate(parent,name):
        if not parent.is_dir():return None
        matches=[p for p in parent.iterdir() if p.name.casefold()==name.casefold()]
        if len(matches)>1:raise ValueError("Ambiguous installation path")
        return matches[0] if matches else None
    binary=locate(root,exe)
    data=locate(root,folder)
    base=locate(data,master) if data is not None else None
    valid=bool(binary and binary.is_file() and base and base.is_file())
    return {"profile":profile,"root":str(root),"executable":str(binary) if binary else None,
            "data":str(data) if data else None,"master":str(base) if base else None,
            "detected":valid,"version":None,"retail_verified":False}

def discover(roots):
    return [row for root in roots for profile in GAMES
            if (row:=inspect(root,profile))["detected"]]
