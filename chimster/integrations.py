"""Explicit, staged adapters for independently installed modding tools."""
from pathlib import Path
import subprocess, tempfile, shutil, os, json
from .loadorder import plugin_name, dependency_order
from .core import inspect_plugin

def executable(path):
    p=Path(path).resolve(strict=True)
    if not p.is_file() or p.suffix.lower() in {".bat",".cmd",".ps1"}:raise ValueError("expected executable, not shell wrapper")
    return str(p)
def file(path,suffixes):
    p=Path(path).resolve(strict=True)
    if not p.is_file() or p.suffix.lower() not in suffixes:raise ValueError("unexpected input file")
    return p
def directory(path):
    p=Path(path).resolve(strict=True)
    if not p.is_dir():raise ValueError("expected directory")
    return p
def fresh(path):
    p=Path(path)
    if p.exists() or p.is_symlink():raise FileExistsError(p)
    if not p.parent.resolve(strict=True).is_dir():raise ValueError("missing parent")
    return p.resolve()
def command(tool,exe,args,output,kind,warning=""):
    return {"tool":tool,"args":[executable(exe),*map(str,args)],"output":str(output),"kind":kind,"warning":warning}

def texconv(exe,source,out,fmt="BC3_UNORM",mips=0):
    source=file(source,{".png",".tga",".dds",".bmp",".jpg",".jpeg",".tif",".tiff"})
    out=fresh(out)
    if fmt not in {"BC1_UNORM","BC3_UNORM","BC5_UNORM","BC7_UNORM","B8G8R8A8_UNORM"} or not isinstance(mips,int) or not 0<=mips<=16:raise ValueError("unsupported format/mip count")
    return command("texconv",exe,["-f",fmt,"-m",mips,"-o",out,source],out,"directory","Choose format compatible with the target game; no BC7 for legacy engines.")

def caprica(exe,source,out,game,imports,flags):
    source=file(source,{".psc"});out=fresh(out);flags=file(flags,{".flg"})
    if game not in {"skyrim","fallout4","fallout76","starfield"}:raise ValueError("unsupported compiler game")
    args=[source,"--game",game,"--output",out,"--flags",flags]
    for folder in imports:args.extend(["--import",directory(folder)])
    return command("caprica",exe,args,out,"directory","Requires appropriate game scripts and flags supplied by user.")

def champollion(exe,source,out):
    return command("champollion",exe,[file(source,{".pex"}),"-p",fresh(out)],Path(out).resolve(),"directory","Decompile only scripts you have rights to modify.")

def spriggit(exe,source,out,game=None,serialize=True):
    out=fresh(out)
    if serialize:
        source=file(source,{".esp",".esm",".esl"})
        if game not in {"SkyrimLE","SkyrimSE","SkyrimVR","Fallout4","Fallout4VR","Oblivion","Starfield"}:raise ValueError("unsupported serialization game")
        args=["serialize","--InputPath",source,"--OutputPath",out,"--GameRelease",game,"--PackageName","Spriggit.Yaml"]
    else:
        source=directory(source)
        if out.suffix.lower() not in {".esp",".esm",".esl"}:raise ValueError("expected plugin output")
        args=["deserialize","--InputPath",source,"--OutputPath",out]
    return command("spriggit",exe,args,out,"tool-owned-directory" if serialize else "file","Spriggit downloads executable NuGet translation packages. Use trusted input, reviewed package versions and a disposable workspace.")

def bsarch(exe,source,out,game):
    source=directory(source);out=fresh(out)
    flags={"morrowind":"-tes3","oblivion":"-tes4","fallout3":"-fo3","newvegas":"-fo3","skyrim":"-tes5","skyrimse":"-sse","fallout4":"-fo4"}
    if game not in flags:raise ValueError("unsupported archive game")
    ext=".ba2" if game=="fallout4" else ".bsa"
    if out.suffix.lower()!=ext or out.is_relative_to(source):raise ValueError("archive must be outside input directory with correct extension")
    if any(p.is_symlink() for p in source.rglob("*")):raise ValueError("symlink in archive source")
    return command("bsarch",exe,["pack",source,out,flags[game]],out,"file","BSArch version/game flags require installed-tool verification.")

def run(plan,timeout=300):
    """Only call with a plan constructed by a typed adapter, never arbitrary JSON."""
    out=fresh(plan["output"])
    if plan["kind"]=="directory":out.mkdir()
    cp=subprocess.run(plan["args"],shell=False,check=False,capture_output=True,text=True,timeout=timeout)
    if cp.returncode:raise RuntimeError(f'{plan["tool"]} failed ({cp.returncode}): {cp.stderr[-4000:]}')
    if not out.exists() or (out.is_dir() and not any(p.is_file() for p in out.rglob("*"))) or (out.is_file() and not out.stat().st_size):raise RuntimeError("tool did not produce output")
    return {"tool":plan["tool"],"output":str(out),"returncode":cp.returncode,"stdout":cp.stdout[-4000:],"status":"output exists; format/engine validation separate"}

def validate_sorted(game,paths,proposed):
    names=[Path(p).name for p in paths]
    if sorted(map(plugin_name,names))!=sorted(map(plugin_name,proposed)):raise ValueError("sort result is not the same plugin set")
    reports={plugin_name(p.name):{"name":p.name,"masters":inspect_plugin(p,game)["masters"]} for p in map(Path,paths)}
    ordered=[reports[plugin_name(n)] for n in proposed]
    if list(map(plugin_name,dependency_order(ordered)))!=list(map(plugin_name,proposed)):raise ValueError("sort result violates masters")
    return proposed
