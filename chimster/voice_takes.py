"""Local voice takes; no identity inference, cloning or cloud uploads."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import uuid
from .audio import publish, wav_info
from .voice_manager import stem

def register(root, source, *, line, performer, rights, notes=""):
    root=Path(root).resolve()
    source=Path(source).resolve(strict=True)
    line=str(stem(line))
    if not isinstance(performer,str) or not performer.strip():
        raise ValueError("performer alias required")
    if not isinstance(rights,str) or not rights.strip():
        raise ValueError("record the permission or license basis")
    data=source.read_bytes()
    if source.suffix.lower()!=".wav":
        raise ValueError("take must be PCM WAV")
    info=wav_info(data)
    digest=hashlib.sha256(data).hexdigest()
    take_id=uuid.uuid4().hex
    folder=root/take_id
    folder.mkdir(parents=True,exist_ok=False)
    row={"id":take_id,"line":line,"performer":performer,"rights":rights,"notes":notes,
         "sha256":digest,"audio":"take.wav","info":info}
    try:
        publish(folder/"take.wav",data)
        publish(folder/"take.json",json.dumps(row,indent=2,ensure_ascii=False).encode("utf-8"))
    except Exception:
        shutil.rmtree(folder)
        raise
    return row

def get(root,take_id):
    if not isinstance(take_id,str) or len(take_id)!=32 or any(x not in "0123456789abcdef" for x in take_id):
        raise ValueError("invalid take ID")
    root=Path(root).resolve(strict=True)
    folder=root/take_id
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError("unsafe take directory")
    meta=folder/"take.json"; sample=folder/"take.wav"
    if meta.is_symlink() or sample.is_symlink():
        raise ValueError("unsafe take files")
    row=json.loads(meta.read_text(encoding="utf-8"))
    if row["id"]!=take_id or row["audio"]!="take.wav":
        raise ValueError("take metadata mismatch")
    stem(row["line"])
    if not isinstance(row.get("rights"),str) or not row["rights"].strip():
        raise ValueError("missing rights declaration")
    data=sample.read_bytes()
    if hashlib.sha256(data).hexdigest()!=row["sha256"]:
        raise ValueError("take hash mismatch")
    wav_info(data)
    return row,data

def list_takes(root,line=None):
    root=Path(root).resolve(strict=True)
    if line is not None: line=str(stem(line)).casefold()
    rows=[]
    for p in sorted(root.iterdir()):
        if p.is_dir() and not p.is_symlink() and (p/"take.json").exists():
            row,_=get(root,p.name)
            if line is None or row["line"].casefold()==line:rows.append(row)
    return rows

def select(root,take_id,staging):
    row,data=get(root,take_id)
    root,staging=Path(root).resolve(),Path(staging).resolve()
    if root==staging or staging.is_relative_to(root) or root.is_relative_to(staging):
        raise ValueError("take registry and staging must be disjoint")
    path=staging/(str(stem(row["line"]))+".wav")
    if not path.resolve().is_relative_to(staging):
        raise ValueError("unsafe staging path")
    path.parent.mkdir(parents=True,exist_ok=True)
    publish(path,data)
    return {"id":take_id,"path":str(path),"sha256":row["sha256"]}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(prog="python -m chimster.voice_takes")
    s=p.add_subparsers(dest="op",required=True)
    a=s.add_parser("register");a.add_argument("root");a.add_argument("source")
    a.add_argument("--line",required=True);a.add_argument("--performer",required=True);a.add_argument("--rights",required=True);a.add_argument("--notes",default="")
    a=s.add_parser("list");a.add_argument("root");a.add_argument("--line")
    a=s.add_parser("select");a.add_argument("root");a.add_argument("id");a.add_argument("staging")
    a=p.parse_args(argv)
    if a.op=="register":r=register(a.root,a.source,line=a.line,performer=a.performer,rights=a.rights,notes=a.notes)
    elif a.op=="list":r=list_takes(a.root,a.line)
    else:r=select(a.root,a.id,a.staging)
    print(json.dumps(r,indent=2,ensure_ascii=False))
if __name__=="__main__":main()
