"""Staged, interactive LOD tool adapters. No invented silent-mode flags."""
from pathlib import Path
import os,subprocess,math,configparser
from .xedit import Workspace,MODES,LOD_MODES
DYN={"skyrim","skyrimse","skyrimvr","enderal","enderalse","fallout4","fallout4vr"}

def tool_plan(workspace,tool,executable):
    p=workspace.paths();game=workspace.game;exe=Path(executable).resolve(strict=True)
    if not exe.is_file():raise ValueError("invalid executable")
    if tool=="xlodgen" and game in LOD_MODES:pass
    elif tool in {"texgen","dyndolod"} and game in DYN:pass
    else:raise ValueError("unsupported tool/game pairing")
    root=workspace.root.resolve();ini=root/"INI";out=root/("LOD-"+tool)
    for d in (ini,out):
        if d.is_symlink() or not d.resolve().is_relative_to(root):raise ValueError("unsafe directory")
    if not ini.is_dir():raise ValueError("supply copied game INIs under INI")
    if out.exists():raise FileExistsError("choose a fresh workspace/output for rebuild")
    def directory(path):return str(path)+os.sep
    args=[str(exe),"-"+MODES[game].lower(),"-d:"+directory(p["data"]),"-p:"+str(p["plugins"]),"-m:"+directory(ini),"-o:"+directory(out),"-t:"+directory(p["temp"])]
    return {"args":args,"cwd":str(exe.parent),"output":str(out),"requires_interactive_review":True}

def run_tool(workspace,tool,executable):
    plan=tool_plan(workspace,tool,executable)
    workspace.paths()["temp"].mkdir(exist_ok=True)
    return subprocess.Popen(plan["args"],cwd=plan["cwd"],shell=False)

def workflow(game):
    if game in DYN:return ["xlodgen terrain","review/install terrain output in staged data","texgen","review/install texture output in staged data","dyndolod","validate all generated records and assets"]
    if game in LOD_MODES:return ["xlodgen terrain/object/tree as supported","validate outputs"]
    if game=="openmw":return ["write proposed paging settings","benchmark runtime"]
    if game=="morrowind":return ["launch MGE XE wizard in disposable game copy","validate distant land outputs"]
    raise ValueError("no enabled LOD workflow")

def openmw_settings(distance=32768,min_size=.023):
    if not math.isfinite(distance) or distance<=0 or not math.isfinite(min_size) or not 0<min_size<=1:raise ValueError("invalid paging settings")
    return "[Camera]\nviewing distance = "+str(distance)+"\n\n[Terrain]\ndistant terrain = true\nobject paging = true\nobject paging min size = "+str(min_size)+"\n"

def mge_plan(game_copy):
    root=Path(game_copy).resolve(strict=True);exe=root/"MGEXEgui.exe"
    if not exe.is_file() or not (root/"Data Files").is_dir():raise ValueError("expected disposable Morrowind installation with MGE XE")
    return {"args":[str(exe)],"cwd":str(root),"requires_interactive_review":True,"warning":"Wizard writes into Data Files; verify this is a disposable game copy."}
