"""Local executable discovery; installation sources are informational only."""
from pathlib import Path
import shutil
from .core import catalog

EXECUTABLES={
    "OpenMW-CS":("openmw-cs","openmw-cs.exe"),
    "NifSkope":("NifSkope.exe","nifskope"),
    "Blender":("blender","blender.exe"),
    "LOOT":("LOOT.exe","loot"),
    "Mod Organizer 2":("ModOrganizer.exe",),
    "Vortex":("Vortex.exe",),
    "DirectXTex / texconv":("texconv.exe","texconv"),
    "BSArch / BSArchPro":("BSArch.exe","BSArchPro.exe"),
    "JPEXS":("ffdec-cli.exe","ffdec"),
    "FFmpeg":("ffmpeg","ffmpeg.exe"),
    "Git":("git","git.exe"),
    "Papyrus Compiler":("PapyrusCompiler.exe",),
    "Caprica":("Caprica.exe","caprica"),
    "Champollion":("Champollion.exe","champollion"),
}
def discover_tools(overrides=None):
    overrides=overrides or {}
    rows=[]
    for name, aliases in EXECUTABLES.items():
        value=overrides.get(name)
        if value:
            p=Path(value).expanduser().resolve()
            found=str(p) if p.is_file() else None
        else:
            found=next((p for a in aliases if (p:=shutil.which(a))),None)
        rows.append({"name":name,"path":found,"status":"detected" if found else "not found"})
    return rows
