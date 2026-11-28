"""Local read-only archive interface."""
from . import classic_bsa,tes3_bsa,ba2_general,ba2_texture
from .compatibility_asset_lookup import normalize
from pathlib import Path
import struct,zlib

def reader(stream):
    stream.seek(0);magic=stream.read(4);stream.seek(0)
    if magic==b"BSA\0":return classic_bsa
    if magic==b"BTDX":
        stream.seek(8);kind=stream.read(4);stream.seek(0)
        return ba2_texture if kind==b"DX10" else ba2_general
    if magic==b"\x00\x01\x00\x00":return tes3_bsa
    raise ValueError("Unsupported archive")

def directory(path):
    try:
        with Path(path).open("rb") as stream:return reader(stream).directory(stream)
    except (struct.error,zlib.error,RuntimeError) as exc:raise ValueError("Invalid archive directory: "+str(exc)) from exc

def read(path,name,limit=64*1024*1024):
    with Path(path).open("rb") as stream:
        adapter=reader(stream)
        entries=adapter.directory(stream)
        key=normalize(name)
        if key not in entries:raise ValueError("Archive member not found: "+key)
        try:return adapter.read(stream,entries[key],limit)
        except (struct.error,zlib.error,RuntimeError) as exc:raise ValueError("Invalid archive member: "+str(exc)) from exc
