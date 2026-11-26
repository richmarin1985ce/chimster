"""Verify the wheel includes the same manual pages as the source tree."""
from pathlib import Path
from zipfile import ZipFile
import subprocess,sys,json,tempfile
root=Path(__file__).resolve().parents[1]
expected={p.relative_to(root/"docs").as_posix():p.read_bytes() for p in (root/"docs").rglob("*") if p.is_file() and p.suffix.lower() in {".md",".txt",".rst"}}
wheels=list((root/"dist").glob("*.whl"))
assert len(wheels)==1,"expected a single built wheel"
with ZipFile(wheels[0]) as z:
    actual={n.removeprefix("chimster/manual/"):z.read(n) for n in z.namelist() if n.startswith("chimster/manual/") and not n.endswith("/")}
assert expected==actual,"wheel documentation differs from source"
with tempfile.TemporaryDirectory() as d:
    subprocess.run([sys.executable,"-m","pip","install","--no-deps","--target",d,str(wheels[0])],check=True)
    result=subprocess.check_output([sys.executable,"-c",f"import sys; sys.path.insert(0,{d!r}); from chimster.wiki import Wiki; import json; w=Wiki(); print(json.dumps(w.pages())); w.close()"],cwd=d,text=True)
    assert {p["id"] for p in json.loads(result)}==set(expected)
print("Verified installed wheel manual:",len(expected),"pages")
