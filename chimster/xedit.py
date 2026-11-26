"""MIT bridge for separately installed xEdit and xLODGen.
Explicit staged paths; no arbitrary AI-written executable scripts.
"""
from dataclasses import dataclass
from pathlib import Path
import shutil, subprocess, json

MODES={"oblivion":"TES4","oblivionremastered":"TES4R","fallout3":"FO3",
       "newvegas":"FNV","skyrim":"TES5","skyrimse":"SSE","skyrimvr":"TES5VR",
       "fallout4":"FO4","fallout4vr":"FO4VR","starfield":"SF1",
       "enderal":"Enderal","enderalse":"EnderalSE","fallout76":"FO76"}
# Conservative initial set; independent of xEdit record support.
LOD_MODES={"oblivion","fallout3","newvegas","skyrim","skyrimse","skyrimvr","fallout4","fallout4vr","enderal","enderalse"}
SCRIPT_DIR=Path(__file__).parent/"xedit_scripts"

def discover(game):
    if game not in MODES: raise ValueError("unsupported xEdit game")
    mode=MODES[game]
    names=[mode+"Edit.exe",mode+"Edit64.exe","xEdit.exe","xEdit64.exe",
           mode+"LODGen.exe",mode+"LODGen64.exe","xLODGen.exe","xLODGen64.exe"]
    return {n:shutil.which(n) for n in names}

@dataclass(frozen=True)
class Workspace:
    root: Path
    game: str

    @classmethod
    def load(cls, path):
        path=Path(path).resolve(strict=True)
        config=json.loads(path.read_text(encoding="utf-8"))
        return cls((path.parent/config["root"]).resolve(),config["game"])

    def paths(self):
        if self.game not in MODES: raise ValueError("unsupported xEdit game")
        root=self.root.resolve(strict=True)
        if not root.is_dir(): raise ValueError("workspace is not a directory")
        # Resolve every path before constructing a command.
        items={k:root/v for k,v in {"data":"Data","plugins":"plugins.txt","output":"LODOutput","cache":"Cache","backup":"Backups","temp":"Temp"}.items()}
        for k,p in items.items():
            if p.is_symlink() or not p.resolve().is_relative_to(root):
                raise ValueError("unsafe workspace path: "+k)
            if k=="plugins":
                if not p.is_file(): raise ValueError("missing workspace plugins.txt")
            elif k=="data":
                if not p.is_dir(): raise ValueError("missing staged Data directory")
                # Do not allow a symlink or hard-linked plugin to point into the live game.
                for child in p.rglob("*"):
                    if child.is_symlink(): raise ValueError("symlink in staging")
                    if child.is_file() and child.suffix.lower() in {".esm",".esp",".esl"} and child.stat().st_nlink!=1:
                        raise ValueError("hard-linked plugin in staging")
            elif p.exists() and not p.is_dir(): raise ValueError("expected directory: "+k)
        return items

def preview(workspace, executable, operation="inspect"):
    paths=workspace.paths()
    exe=Path(executable).resolve(strict=True)
    if not exe.is_file(): raise ValueError("invalid executable")
    args=[str(exe),"-"+MODES[workspace.game],"-D:"+str(paths["data"]),
          "-P:"+str(paths["plugins"]),"-C:"+str(paths["cache"]),
          "-B:"+str(paths["backup"]),"-T:"+str(paths["temp"])]
    if operation=="inspect":
        args+=["-S:"+str(SCRIPT_DIR)]
    elif operation=="conflicts":
        args+=["-quickshowconflicts"]
    elif operation=="lod":
        if workspace.game not in LOD_MODES: raise ValueError("LOD adapter not enabled for this game")
        args+=["-O:"+str(paths["output"])]
    else: raise ValueError("unsupported operation")
    return {"operation":operation,"args":args,"cwd":str(exe.parent),
            "warning":"Interactive tool, not a sandbox. Use copied mod data only. Review all changes before saving."}

def launch(workspace, executable, operation="inspect"):
    plan=preview(workspace,executable,operation)
    paths=workspace.paths()
    for k in ("output","cache","backup","temp"):
        paths[k].mkdir(exist_ok=True)
    return subprocess.Popen(plan["args"],cwd=plan["cwd"],shell=False)

def report_from_log(text):
    """Parse marker-prefixed audit lines. Form IDs are load-order-relative."""
    results=[]
    for line in text.splitlines():
        marker="CHIMSTER_AUDIT|"
        if not line.startswith(marker): continue
        fields=line[len(marker):].split("|")
        if len(fields)!=6: raise ValueError("malformed audit line")
        sig,plugin,formid,editorid,model,winner=fields
        if len(sig)!=4 or len(formid)!=8 or any(c not in "0123456789abcdefABCDEF" for c in formid) or winner not in {"0","1"}:
            raise ValueError("invalid audit record")
        results.append({"signature":sig,"plugin":plugin,"load_order_formid":formid,
                        "editorid":editorid,"model":model,"winning":winner=="1"})
    return results
