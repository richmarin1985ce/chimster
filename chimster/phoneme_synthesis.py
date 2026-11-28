"""Experimental native synthesis from explicitly observed slots."""
import hashlib
import json
import math
from pathlib import Path
import struct
from . import audio, lip_curves as lc, morph_calibration as mc
from . import _openfacefx_lip_codec as codec

def frames(rows,duration,calibration,transition=.04):
    if not 0<duration<=300 or not math.isfinite(transition) or not 0<=transition<=.25:
        raise ValueError("unsupported duration or transition")
    segments=mc.preview(rows,duration,calibration)["segments"]
    slots=sorted({int(s) for r in segments for s,w in r["slots"].items() if w>0})
    if len(set(slots)|{0})>16:raise ValueError("at most 16 active slots including anchor")
    result=[];i=0
    for n in range(math.ceil(duration*30)+1):
        t=min(n/30,duration)
        while i<len(segments) and segments[i]["end"]<=t:i+=1
        weights={}
        if i<len(segments):
            r=segments[i]
            if r["start"]<=t<r["end"]:
                ramp=min(transition,(r["end"]-r["start"])/2)
                scale=1 if not ramp else min(1,(t-r["start"])/ramp,(r["end"]-t)/ramp)
                weights={int(s):round(w*scale,5) for s,w in r["slots"].items()}
        result.append({s:weights.get(s,0.) for s in slots})
    return result,slots

def synthesize(rows,duration,calibration,*,transition=.04,experimental=False):
    if not experimental:raise ValueError("explicit experimental Skyrim export required")
    grid,slots=frames(rows,duration,calibration,transition)
    if not slots:raise ValueError("no active morph weights")
    count=len(grid);stride=33;active=sorted(set(slots)|{0});cells=[]
    for n,row in enumerate(grid):
        for s in active:
            v=row.get(s,0.)
            if v==0:v=codec.SENTINEL if s%2==0 else 0.
            cells.append({"frame":n,"curve":s,"value":v})
    # Unresolved u22 follows the upstream research writer.
    header=struct.pack("<IIIHHiHH",1,132*count+28,len(active),count,3,0,16,3)
    blob=header+codec.encode_curves(cells,stride,total_slots=count*stride)
    _,decoded,_=lc.decode(blob)
    def identity(c):return (c["frame"],c["curve"],struct.pack("<f",c["value"]))
    if list(map(identity,cells))!=list(map(identity,decoded)) or any(c["dup"] for c in decoded):
        raise ValueError("ambiguous native encoding; adjust adjacent identical slot weights")
    return blob

def build(wav,rows,calibration,output,*,transition=.04,experimental=False):
    data=Path(wav).read_bytes();duration=audio.wav_info(data)["duration"]
    blob=synthesize(rows,duration,calibration,transition=transition,experimental=experimental)
    def sha(b):return hashlib.sha256(b).hexdigest()
    def jb(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False).encode("utf-8")
    report={"game":"Skyrim","experimental":True,"runtime_verified":False,
            "source_sha256":sha(data),"timeline_sha256":sha(jb(rows)),
            "profile_sha256":sha(jb(calibration)),"lip_sha256":sha(blob),
            "transition_seconds":transition,"frames":lc.inspect(blob)["header"]["frames"]}
    output=Path(output);output.mkdir()
    try:
        audio.publish(output/"voice.lip",blob)
        audio.publish(output/"receipt.json",jb(report))
    except Exception:
        for n in ("voice.lip","receipt.json"):(output/n).unlink(missing_ok=True)
        output.rmdir();raise
    return report

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();p.add_argument("wav");p.add_argument("timeline");p.add_argument("profile");p.add_argument("output")
    p.add_argument("--transition",type=float,default=.04);p.add_argument("--experimental",action="store_true")
    a=p.parse_args(argv)
    def load(x):return json.loads(Path(x).read_text(encoding="utf-8"))
    print(json.dumps(build(a.wav,load(a.timeline),load(a.profile),a.output,transition=a.transition,experimental=a.experimental),indent=2))
if __name__=="__main__":main()
