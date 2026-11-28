"""Explicit local native LIP generation, with separate experimental backend."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
import tempfile
from . import audio

MAX_LIP = 64 * 1024 * 1024

def digest(data):
    return hashlib.sha256(data).hexdigest()

def header(data, game=None):
    """Inspect the observed native frame-grid header, not the wrapper ABI."""
    if not 24 < len(data) <= MAX_LIP:
        raise ValueError("missing or oversized native LIP payload")
    version,ticks,curves,frames,components,first,targets,unknown = struct.unpack_from("<IIIHHiHH",data)
    if version!=1 or not frames or not curves or components!=3:
        raise ValueError("unsupported native LIP header")
    detected={16:"Skyrim",43:"Fallout4"}.get(targets)
    if detected is None or game is not None and detected!=game:
        raise ValueError("unsupported or mismatched native target count")
    stride={"Skyrim":132,"Fallout4":240}[detected]
    if ticks!=stride*frames+28:
        raise ValueError("unsupported native time-grid invariant")
    return {"version":version,"game":detected,"duration_ticks":ticks,
            "frames":frames,"first_frame":first,"active_curves":curves,
            "target_count":targets,"components":components,"unknown_u22":unknown,
            "payload_bytes":len(data)-24,
            "validation":"observed native header only; curve payload and runtime unverified"}


def build(source, output, *, game, transcript, tool, backend="facefxwrapper",
          fonix=None, ffmpeg=None, experimental=False):
    if game not in ("Skyrim","Fallout4") or not isinstance(transcript,str) or not transcript.strip():
        raise ValueError("supported game and transcript required")
    source=Path(source).resolve(strict=True)
    out=Path(output)
    if out.exists() or out.is_symlink():
        raise FileExistsError(out)
    original=source.read_bytes()
    info=audio.wav_info(original)
    exe=audio.executable(tool)
    tool_hash=digest(Path(exe).read_bytes())
    if backend=="openfacefx":
        if game!="Skyrim" or not experimental:
            raise ValueError("OpenFaceFX native export is experimental and Skyrim-only")
    elif backend=="facefxwrapper":
        if fonix is None:
            raise ValueError("supply licensed FonixData.cdf")
        fonix=Path(fonix).resolve(strict=True)
        if not fonix.is_file() or not fonix.stat().st_size:
            raise ValueError("invalid Fonix data")
    else:
        raise ValueError("unknown backend")
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)
        wav=tmp/"input.wav";wav.write_bytes(original)
        if (info["channels"],info["sample_width"],info["sample_rate"])!=(1,2,16000):
            if not ffmpeg:raise ValueError("normalize WAV first or configure FFmpeg")
            normalized=tmp/"normalized.wav"
            audio.convert(wav,normalized,ffmpeg,"normalize");wav=normalized
        lip=tmp/"voice.lip"
        if backend=="openfacefx":
            audio.run_tool([exe,"naive","--text",transcript,"--wav",str(wav),"-o",str(lip)])
        else:
            audio.native_lip(wav,lip,exe,fonix,game,transcript)
        if lip.stat().st_size>MAX_LIP:raise ValueError("oversized LIP")
        data=lip.read_bytes()
        meta=header(data,game)
        if digest(Path(exe).read_bytes())!=tool_hash:
            raise ValueError("backend executable changed during generation")
        report={"game":game,"backend":backend,"experimental":backend=="openfacefx",
                "tool_sha256":tool_hash,"source_sha256":digest(original),
                "normalized_sha256":digest(wav.read_bytes()),
                "transcript_sha256":digest(transcript.encode("utf-8")),
                "lip_sha256":digest(data),"header":meta,"runtime_verified":False}
        # Publish a new directory as a pair; no existing voice asset is overwritten.
        out.mkdir()
        try:
            audio.publish(out/"voice.lip",data)
            audio.publish(out/"receipt.json",json.dumps(report,indent=2).encode("utf-8"))
        except Exception:
            for name in ("voice.lip","receipt.json"):(out/name).unlink(missing_ok=True)
            out.rmdir()
            raise
        return report

def verify(directory, source, transcript):
    directory=Path(directory)
    report=json.loads((directory/"receipt.json").read_text(encoding="utf-8"))
    data=(directory/"voice.lip").read_bytes()
    header(data,report["game"])
    return {"game":report["game"],"lip_matches":digest(data)==report["lip_sha256"],
            "audio_matches":digest(Path(source).read_bytes())==report["source_sha256"],
            "transcript_matches":digest(transcript.encode("utf-8"))==report["transcript_sha256"],
            "runtime_verified":False,"experimental":report["experimental"]}

def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(prog="python -m chimster.lip_pipeline")
    s=p.add_subparsers(dest="op",required=True)
    a=s.add_parser("build")
    a.add_argument("source");a.add_argument("output");a.add_argument("--game",choices=("Skyrim","Fallout4"),required=True)
    a.add_argument("--transcript",required=True);a.add_argument("--tool",required=True)
    a.add_argument("--backend",choices=("facefxwrapper","openfacefx"),default="facefxwrapper")
    a.add_argument("--fonix");a.add_argument("--ffmpeg");a.add_argument("--experimental",action="store_true")
    a=s.add_parser("verify");a.add_argument("directory");a.add_argument("source");a.add_argument("--transcript",required=True)
    a=s.add_parser("inspect");a.add_argument("lip",type=Path)
    a=p.parse_args(argv)
    if a.op=="build":
        result=build(a.source,a.output,game=a.game,transcript=a.transcript,tool=a.tool,backend=a.backend,fonix=a.fonix,ffmpeg=a.ffmpeg,experimental=a.experimental)
    elif a.op=="verify":result=verify(a.directory,a.source,a.transcript)
    else:result=header(a.lip.read_bytes())
    print(json.dumps(result,indent=2))
    if a.op=="verify" and not all(result[k] for k in ("lip_matches","audio_matches","transcript_matches")):raise SystemExit(1)

if __name__=="__main__":main()
