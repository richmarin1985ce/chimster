"""Save validated native plugin bytes without truncating the original."""
import hashlib
import os
from pathlib import Path
import tempfile
from .native_parser import parse,subrecords

def save(profile,data,destination,*,expected_disk_revision=None):
    nodes=parse(profile,data)
    if not nodes or nodes[0].signature not in (b"TES3",b"TES4"):raise ValueError("Missing plugin header")
    def validate(nodes):
        for node in nodes:
            if node.signature==b"GRUP":validate(node.children)
            else:list(subrecords(profile,node))
    validate(nodes)
    path=Path(destination)
    if path.is_symlink():raise ValueError("Refusing symlink destination")
    def check():
        if path.exists():
            if expected_disk_revision is None:raise FileExistsError(path)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=expected_disk_revision:raise ValueError("File changed on disk")
        elif expected_disk_revision is not None:raise ValueError("Original file missing")
    check()
    fd,tmp=tempfile.mkstemp(prefix=".chimster-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        check()
        if expected_disk_revision is None:
            os.link(tmp,path)
        else:
            os.replace(tmp,path)
        return hashlib.sha256(data).hexdigest()
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
