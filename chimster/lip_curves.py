"""Experimental native LIP curve editor. Slot IDs are not named morphs."""
from __future__ import annotations
import csv
import io
import json
import math
from pathlib import Path
import struct
from . import _openfacefx_lip_codec as codec
from .lip_pipeline import header
from .audio import publish

MAX_CELLS = 1_000_000
MAX_FILE = 8 * 1024 * 1024

def read(path):
    p=Path(path)
    if p.stat().st_size>MAX_FILE:
        raise ValueError("native curve editor size limit exceeded")
    return p.read_bytes()

def decode(data):
    if len(data)>MAX_FILE:raise ValueError("native curve editor size limit exceeded")
    meta=header(data)
    tokens,end=codec.parse_payload(data)
    if end!=len(data) or not tokens or len(tokens)>MAX_CELLS:
        raise ValueError("incomplete or oversized token stream")
    cells,stride,stop=codec.decode_cells(data)
    if stop>stride*meta["frames"] or stop<=stride*(meta["frames"]-1):
        raise ValueError("frame-grid extent mismatch")
    if any(not math.isfinite(c["value"]) or c["pos"]+(2 if c["dup"] else 1)>stride*meta["frames"] for c in cells):
        raise ValueError("invalid curve cell")
    exact,rebuilt=codec.roundtrip_curves(data)
    if not exact or rebuilt!=data:raise ValueError("codec cannot reproduce this file")
    return meta,cells,stride

def inspect(data):
    meta,cells,stride=decode(data)
    slots={}
    for c in cells:
        v=0.0 if c["is_sentinel"] else c["value"]
        s=slots.setdefault(c["curve"],{"keys":0,"min":v,"max":v,"duplicate_tokens":0})
        s["keys"]+=1;s["min"]=min(s["min"],v);s["max"]=max(s["max"],v);s["duplicate_tokens"]+=int(c["dup"])
    return {"header":meta,"stride":stride,"slots":slots,"byte_exact":True,
            "runtime_verified":False,"mapping":"raw slot indices, not calibrated morph names"}

def export_csv(data):
    _,cells,_=decode(data)
    out=io.StringIO(newline="")
    w=csv.writer(out);w.writerow(["frame","slot","raw_value","dup","sentinel"])
    for c in cells:w.writerow([c["frame"],c["curve"],repr(c["value"]),int(c["dup"]),int(c["is_sentinel"])])
    return out.getvalue()

def edit(data, changes, *, experimental=False):
    if not experimental:raise ValueError("explicit experimental native edit opt-in required")
    meta,cells,stride=decode(data)
    if meta["game"]!="Skyrim":
        raise ValueError("Fallout 4 native curve writing not enabled; inspect only")
    if not isinstance(changes,list) or not changes:raise ValueError("provide nonempty edits")
    index={(c["frame"],c["curve"]):c for c in cells}
    seen=set()
    for row in changes:
        if not isinstance(row,dict) or set(row)!={"frame","slot","value"}:
            raise ValueError("edit requires frame, slot, value")
        if type(row["frame"]) is not int or type(row["slot"]) is not int:
            raise ValueError("frame and slot must be integer")
        key=(row["frame"],row["slot"])
        if key in seen or key not in index:raise ValueError("duplicate or nonexistent key")
        seen.add(key)
        c=index[key]
        if c["dup"]:
            raise ValueError("equal-value/tangent pairs are read-only")
        v=row["value"]
        if type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1:
            raise ValueError("edited weights must be finite 0..1")
        c["value"]=struct.unpack("<f",struct.pack("<f",v))[0]
    tail=cells[-1]["marker"]
    result=data[:24]+codec.encode_curves(cells,stride,tail_marker=tail)
    _,check,_=decode(result)
    if len(check)!=len(cells):raise ValueError("edit introduced ambiguous token encoding")
    for a,b in zip(cells,check):
        if (a["pos"],a["dup"],a["marker"],struct.pack("<f",a["value"]))!=(b["pos"],b["dup"],b["marker"],struct.pack("<f",b["value"])):
            raise ValueError("edit changed native routing or quantized value")
    return result

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(prog="python -m chimster.lip_curves")
    s=p.add_subparsers(dest="op",required=True)
    a=s.add_parser("inspect");a.add_argument("source")
    a=s.add_parser("csv");a.add_argument("source");a.add_argument("output")
    a=s.add_parser("edit");a.add_argument("source");a.add_argument("changes");a.add_argument("output");a.add_argument("--experimental",action="store_true")
    a=p.parse_args(argv);data=read(a.source)
    if a.op=="inspect":print(json.dumps(inspect(data),indent=2))
    elif a.op=="csv":publish(Path(a.output),export_csv(data).encode("utf-8"))
    else:
        if Path(a.output).suffix.lower()!=".lip":raise ValueError("choose new .lip file")
        publish(Path(a.output),edit(data,json.loads(Path(a.changes).read_text(encoding="utf-8")),experimental=a.experimental))
if __name__=="__main__":main()
