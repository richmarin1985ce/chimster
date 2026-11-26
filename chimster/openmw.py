"""MIT adapter for independently installed OpenMW; no OpenMW code included."""
from dataclasses import dataclass
from pathlib import Path
import json, shutil, subprocess

EXTENSIONS={".esm",".esp",".omwgame",".omwaddon",".omwscripts"}

def discover():
    return {name:shutil.which(name) for name in ("openmw","openmw-cs","openmw-launcher","openmw-iniimporter")}

@dataclass(frozen=True)
class Profile:
    root: Path
    data: tuple[Path,...]
    content: tuple[str,...]
    archives: tuple[str,...]=()

    @property
    def staging(self): return self.root.resolve()/"data"
    @property
    def userdata(self): return self.root.resolve()/"userdata"

    def validate(self):
        if not self.data or not self.content:
            raise ValueError("explicit data directories and content order required")
        root=self.root.resolve()
        dirs=[p.resolve(strict=True) for p in self.data]
        if any(not p.is_dir() for p in dirs):
            raise ValueError("data path is not a directory")
        if any(root==p or root.is_relative_to(p) or p.is_relative_to(root) for p in dirs):
            raise ValueError("workspace and input directories must be separate")
        if len(set(dirs))!=len(dirs): raise ValueError("duplicate data directory")
        if any(p.is_symlink() for p in (self.root/"data",self.root/"userdata")):
            raise ValueError("workspace output must not be a symlink")
        for names,extensions in ((self.content,EXTENSIONS),(self.archives,{".bsa"})):
            if len({n.casefold() for n in names})!=len(names):
                raise ValueError("duplicate filename in load order")
            for n in names:
                if not n or n.startswith("-") or any(c in n for c in '/\\\r\n\0:') or Path(n).suffix.lower() not in extensions:
                    raise ValueError("invalid content/archive filename: "+n)
                if not any((p/n).is_file() for p in [self.staging,*reversed(dirs)]):
                    raise ValueError("missing content/archive: "+n)
        return dirs

    def engine_args(self):
        dirs=self.validate()
        args=["--replace","config","--replace","data","--replace","content","--replace","fallback-archive",
              "--user-data",str(self.userdata),"--data-local",str(self.staging)]
        for p in dirs: args.extend(["--data",str(p)])
        for n in self.archives: args.extend(["--fallback-archive",n])
        for n in self.content: args.extend(["--content",n])
        return args

    def prepare(self):
        self.validate()
        self.staging.mkdir(parents=True,exist_ok=True)
        self.userdata.mkdir(parents=True,exist_ok=True)

    @classmethod
    def load(cls,path):
        path=Path(path).resolve()
        obj=json.loads(path.read_text(encoding="utf-8"))
        def resolve(p): return (path.parent/Path(p)).resolve()
        return cls(resolve(obj["root"]),tuple(resolve(p) for p in obj["data"]),tuple(obj["content"]),tuple(obj.get("archives",[])))

def launch_game(profile, executable=None):
    binary=executable or discover()["openmw"]
    if not binary: raise FileNotFoundError("OpenMW not found; install or specify its executable")
    binary=Path(binary).resolve(strict=True)
    args=profile.engine_args()
    profile.prepare()
    return subprocess.Popen([str(binary),*args],cwd=str(binary.parent),shell=False)

def launch_editor(executable=None):
    """Uses installed editor's normal profile. No isolation claim."""
    binary=executable or discover()["openmw-cs"]
    if not binary: raise FileNotFoundError("OpenMW-CS not found")
    binary=Path(binary).resolve(strict=True)
    return subprocess.Popen([str(binary)],cwd=str(binary.parent),shell=False)

def reload_plan(changed):
    paths=[str(p) for p in changed]
    if paths and all(Path(p).suffix.lower()==".lua" for p in paths):
        return {"action":"manual-console","command":"reloadlua","reason":"Lua source only; runtime compatibility must be checked"}
    return {"action":"restart","reason":"Content registration, records, assets or unknown changes require conservative restart"}
