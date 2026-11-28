"""OpenMW Lua 5.1 syntax validation through an explicitly installed luac."""
from pathlib import Path
import re, subprocess, tempfile, shutil
from .integrations import executable, file
from .papyrus_build import digest
from .compiler_diagnostics import parse,summarize

def check(exe,source,*,execute=False,timeout=30):
    if type(timeout) is not int or not 1<=timeout<=300:raise ValueError("invalid timeout")
    binary=executable(exe);src=file(source,{".lua"})
    if src.stat().st_size>2*1024*1024:raise ValueError("Lua source too large")
    report={"backend":"luac-5.1","args":[binary,"-p",str(src)],
            "source":str(src),"source_sha256":digest(src),"compiler_sha256":digest(binary),
            "scope":"Lua 5.1 syntax validation only; OpenMW extensions/API/runtime not certified"}
    if not execute:return report
    try:
        with tempfile.TemporaryDirectory(prefix="chimster-lua-") as d:
            version=subprocess.run([binary,"-v"],shell=False,cwd=d,capture_output=True,text=True,errors="replace",timeout=timeout)
            version_text=version.stdout+"\n"+version.stderr
            if version.returncode or not re.search(r"\bLua 5\.1(?:\.\d+)?\b",version_text):
                return {**report,"status":"unsupported-version","version":version_text}
            copy=Path(d)/src.name;shutil.copyfile(src,copy)
            if digest(copy)!=report["source_sha256"]:return {**report,"status":"inputs-changed"}
            cp=subprocess.run([binary,"-p",str(copy)],shell=False,cwd=d,capture_output=True,text=True,errors="replace",timeout=timeout)
            items=parse(cp.stdout,stream="stdout")+parse(cp.stderr,stream="stderr")
            for item in items:
                if item.get("file")==str(copy):item["file"]=str(src)
            status="syntax-checked" if cp.returncode==0 else "syntax-failed"
            if digest(src)!=report["source_sha256"] or digest(binary)!=report["compiler_sha256"]:status="inputs-changed"
            return {**report,"status":status,"version":version_text.strip(),"returncode":cp.returncode,
                    "diagnostics":items,"summary":summarize(items)}
    except subprocess.TimeoutExpired:return {**report,"status":"timeout"}
    except OSError as exc:return {**report,"status":"launch-failed","message":str(exc)}
