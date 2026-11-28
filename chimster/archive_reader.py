"""Local read-only archive interface."""
from . import classic_bsa,tes3_bsa,ba2_general
from .compatibility_asset_lookup import normalize
from pathlib import Path

def reader(stream):
    stream.seek(0);magic=stream.read(4);stream.seek(0)
    if magic==b"BSA\0":return classic_bsa
    if magic==b"BTDX":return ba2_general
    if magic==b"\x00\x01\x00\x00":return tes3_bsa
    raise ValueError("Unsupported archive")

def directory(path):
    with Path(path).open("rb") as stream:return reader(stream).directory(stream)

def read(path,name,limit=64*1024*1024):
    with Path(path).open("rb") as stream:
        adapter=reader(stream)
        entries=adapter.directory(stream)
        return adapter.read(stream,entries[normalize(name)],limit)
