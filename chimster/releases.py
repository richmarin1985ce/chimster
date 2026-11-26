"""Deterministic local package builder for an explicitly staged mod."""
from pathlib import Path
from hashlib import sha256
import json
import zipfile

def package(staging: Path, output: Path) -> dict:
    root = staging.resolve(strict=True)
    output = output.resolve()
    if not root.is_dir() or output.is_relative_to(root):
        raise ValueError("package output must be outside staging")
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            raise ValueError("symlinks are not allowed")
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            if any(part.startswith(".") for part in p.relative_to(root).parts):
                raise ValueError("hidden file in staging: " + rel)
            if rel.casefold() == "chimster-manifest.json":
                raise ValueError("reserved filename")
            files.append((rel, p.read_bytes()))
    if not files:
        raise ValueError("empty staging directory")
    if len({rel.casefold() for rel, _ in files}) != len(files):
        raise ValueError("case-insensitive filename collision")
    manifest = {"files": [{"path": rel, "sha256": sha256(data).hexdigest(), "size": len(data)} for rel,data in files]}
    def add(z, name, data):
        info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, data)
    with zipfile.ZipFile(output, "x") as z:
        for rel, data in files:
            add(z, rel, data)
        add(z, "chimster-manifest.json", json.dumps(manifest, sort_keys=True).encode())
    return manifest
