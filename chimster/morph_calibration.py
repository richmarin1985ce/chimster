"""Experimental Skyrim raw-slot calibration and language-neutral morph mapping."""
from pathlib import Path
import json
import math
import struct
import tempfile
from . import audio, lip_curves as lc
from . import _openfacefx_lip_codec as codec
from .phoneme_import import validate

def probes(output, tool="openfacefx", seconds=2.0):
    if not math.isfinite(seconds) or not .5<=seconds<=10:
        raise ValueError("probe duration must be 0.5–10 seconds")
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)/"probes"
        audio.run_tool([audio.executable(tool),"lip-calibrate","--out",str(root),"--seconds",str(seconds),"--lip-game","skyrim"])
        files={}
        for slot in range(33):
            name=f"slot_{slot:02d}.lip";data=lc.read(root/name)
            meta,cells,_=lc.decode(data)
            if meta["game"]!="Skyrim" or not any(c["curve"]==slot and c["value"]>.99 for c in cells):
                raise ValueError("unexpected calibration probe")
            files[name]=data
        observations={"schema":1,"game":"Skyrim","observations":{str(s):{"morph":"","observed":False,"notes":""} for s in range(33)}}
        output.mkdir()
        for name,data in files.items():audio.publish(output/name,data)
        audio.publish(output/"observations.json",json.dumps(observations,indent=2).encode())
        return observations

def profile(obj):
    if obj.get("schema")!=1 or obj.get("game")!="Skyrim":
        raise ValueError("expected Skyrim calibration profile")
    obs=obj.get("observations")
    if not isinstance(obs,dict) or set(obs)!={str(s) for s in range(33)}:
        raise ValueError("record all 33 slots (unobserved slots are allowed)")
    for s,row in obs.items():
        if type(row.get("observed")) is not bool or not isinstance(row.get("morph"),str):
            raise ValueError("invalid slot observation")
        if row["observed"] and not row["morph"].strip():raise ValueError("observed slot needs a label; use none if inactive")
    mappings=obj.get("phonemes",{})
    if not isinstance(mappings,dict):raise ValueError("invalid phoneme mapping")
    for ph,weights in mappings.items():
        if not isinstance(ph,str) or not ph.strip() or not isinstance(weights,dict):raise ValueError("invalid phoneme")
        for slot,w in weights.items():
            if slot not in obs or not obs[slot]["observed"] or obs[slot]["morph"].strip().casefold()=="none":
                raise ValueError("mapping references unobserved or inactive slot")
            if type(w) not in (int,float) or not math.isfinite(w) or not 0<=w<=1:
                raise ValueError("invalid morph weight")
    return obj

def preview(rows,duration,calibration):
    rows=validate(rows,duration);calibration=profile(calibration)
    mapping=calibration.get("phonemes",{})
    missing=sorted({r["phoneme"] for r in rows if r["phoneme"] not in mapping and r["phoneme"]!="sil"})
    if missing:raise ValueError("unmapped phonemes: "+", ".join(missing))
    return {"game":"Skyrim","duration":duration,"runtime_verified":False,
            "segments":[{**r,"slots":mapping.get(r["phoneme"],{})} for r in rows]}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();s=p.add_subparsers(dest="op",required=True)
    a=s.add_parser("probes");a.add_argument("output");a.add_argument("--tool",default="openfacefx");a.add_argument("--seconds",type=float,default=2)
    a=s.add_parser("preview");a.add_argument("timeline");a.add_argument("profile");a.add_argument("wav");a.add_argument("output")
    a=p.parse_args(argv)
    if a.op=="probes":probes(a.output,a.tool,a.seconds)
    else:
        duration=audio.wav_info(Path(a.wav).read_bytes())["duration"]
        rows=json.loads(Path(a.timeline).read_text(encoding="utf-8"))
        cal=json.loads(Path(a.profile).read_text(encoding="utf-8"))
        audio.publish(Path(a.output),json.dumps(preview(rows,duration,cal),indent=2,ensure_ascii=False).encode("utf-8"))
if __name__=="__main__":main()
