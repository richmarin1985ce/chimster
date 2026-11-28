"""Staged Champollion decompilation for the supported Papyrus families."""
from pathlib import Path
import json
import subprocess
import tempfile
import shutil
from .integrations import executable, file, fresh
from .papyrus_build import inspect_pex, digest
from .compiler_diagnostics import parse, summarize
from .script_lint import check_file

def decompile(game,exe,source,output,*,execute=False,timeout=120):
    if type(timeout) is not int or not 1<=timeout<=900:raise ValueError("invalid timeout")
    src=file(source,{".pex"});binary=executable(exe);out=fresh(output)
    header=inspect_pex(src,game)
    report={"game":game,"backend":"champollion","source":str(src),"input":header,
            "compiler_sha256":digest(binary),"output":str(out),
            "args":[binary,str(src),"-p",str(out)],
            "scope":"recovered source, not guaranteed original or semantically equivalent"}
    if not execute:return report
    with tempfile.TemporaryDirectory(prefix=".chimster-decompile-",dir=out.parent) as t:
        root=Path(t);copy=root/src.name;stage=root/"psc";stage.mkdir()
        shutil.copyfile(src,copy)
        if digest(copy)!=header["sha256"]:return {**report,"status":"inputs-changed"}
        try:
            cp=subprocess.run([binary,str(copy),"-p",str(stage)],cwd=t,shell=False,
                              capture_output=True,text=True,errors="replace",timeout=timeout)
        except subprocess.TimeoutExpired:return {**report,"status":"timeout"}
        except OSError as exc:return {**report,"status":"launch-failed","message":str(exc)}
        items=parse(cp.stdout,stream="stdout")+parse(cp.stderr,stream="stderr")
        report.update(returncode=cp.returncode,diagnostics=items,summary=summarize(items))
        if cp.returncode:return {**report,"status":"decompiler-failed"}
        files=list(stage.iterdir())
        if len(files)!=1 or files[0].is_symlink() or not files[0].is_file() or files[0].suffix.casefold()!=".psc" or files[0].stem.casefold()!=src.stem.casefold():
            return {**report,"status":"unexpected-output"}
        recovered=files[0]
        try:
            lint=check_file(recovered)
            if lint["script_names"]!=[src.stem.casefold()]:raise ValueError("recovered Scriptname mismatch")
        except (OSError,ValueError) as exc:return {**report,"status":"invalid-source","message":str(exc)}
        if digest(src)!=header["sha256"] or digest(binary)!=report["compiler_sha256"]:
            return {**report,"status":"inputs-changed"}
        report.update(status="source-recovered",lint=lint,artifact={"name":recovered.name,"sha256":digest(recovered)})
        out.mkdir();created=[]
        try:
            dst=out/recovered.name
            with dst.open("xb") as f:
                created.append(dst);f.write(recovered.read_bytes())
            if digest(dst)!=report["artifact"]["sha256"]:raise ValueError("artifact changed")
            manifest=out/"decompile.json"
            with manifest.open("x",encoding="utf-8") as f:
                created.append(manifest);json.dump(report,f,indent=2)
        except Exception:
            for p in reversed(created):p.unlink(missing_ok=True)
            out.rmdir();raise
        return report
