"""External JPEXS extraction/import bridge for SWF, not a native editor."""
from pathlib import Path
import subprocess, shutil
def command_prefix(executable):
    exe=Path(executable).resolve(strict=True)
    if not exe.is_file():raise ValueError("invalid FFDec executable")
    if exe.suffix.lower()==".jar":
        java=shutil.which("java")
        if not java:raise FileNotFoundError("Java not found")
        return [java,"-jar",str(exe)]
    if exe.suffix.lower() in {".bat",".cmd"}:raise ValueError("use CLI executable or JAR, not a shell wrapper")
    return [str(exe)]
def export_plan(executable,source,output):
    source=Path(source).resolve(strict=True);output=Path(output).resolve()
    if not source.is_file() or source.suffix.lower()!=".swf" or output.exists():raise ValueError("expected SWF and a new output directory")
    return command_prefix(executable)+["-export","script,image,shape,font,text",str(output),str(source)]
def import_plan(executable,source,output,scripts):
    source=Path(source).resolve(strict=True);output=Path(output).resolve();scripts=Path(scripts).resolve(strict=True)
    if not source.is_file() or source.suffix.lower()!=".swf" or output.suffix.lower()!=".swf" or output.exists() or not scripts.is_dir():raise ValueError("expected original SWF, new output SWF, and scripts directory")
    return command_prefix(executable)+["-importScript",str(source),str(output),str(scripts)]
def execute(args):
    return subprocess.run(args,check=True,shell=False,capture_output=True,text=True)
