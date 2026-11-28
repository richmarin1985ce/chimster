"""Bounded microphone capture using separately installed sounddevice/PortAudio."""
from __future__ import annotations
import io
import math
from pathlib import Path
import wave
from .audio import publish

def backend():
    try:
        import sounddevice
    except ImportError as exc:
        raise ValueError("install optional sounddevice and PortAudio to record") from exc
    return sounddevice

def devices(sd=None):
    sd=sd or backend()
    return [{"index":i,"name":d["name"],"channels":int(d["max_input_channels"]),
             "default_rate":float(d["default_samplerate"])}
            for i,d in enumerate(sd.query_devices()) if d["max_input_channels"]>0]

def record(seconds, device, *, rate=16000, channels=1, sd=None, cancelled=None):
    if not isinstance(seconds,(float,int)) or not math.isfinite(seconds) or not 0.1<=seconds<=300:
        raise ValueError("recording length must be 0.1 to 300 seconds")
    if rate not in (16000,22050,44100,48000) or channels not in (1,2):
        raise ValueError("unsupported PCM capture format")
    if type(device) is not int or device<0:
        raise ValueError("choose an explicit input device")
    sd=sd or backend()
    sd.check_input_settings(device=device,channels=channels,dtype="int16",samplerate=rate)
    remaining=round(seconds*rate);buffer=bytearray()
    with sd.RawInputStream(device=device,channels=channels,dtype="int16",samplerate=rate) as stream:
        while remaining:
            if cancelled and cancelled():raise ValueError("recording cancelled")
            n=min(remaining,1024)
            block,overflow=stream.read(n)
            if overflow or len(block)!=n*channels*2:
                raise ValueError("input overflow or short recording; retry")
            buffer.extend(block);remaining-=n
    if cancelled and cancelled():raise ValueError("recording cancelled")
    out=io.BytesIO()
    with wave.open(out,"wb") as f:
        f.setnchannels(channels);f.setsampwidth(2);f.setframerate(rate);f.writeframes(buffer)
    return out.getvalue()

def main(argv=None):
    import argparse,json
    p=argparse.ArgumentParser(prog="python -m chimster.voice_record")
    s=p.add_subparsers(dest="op",required=True);s.add_parser("devices")
    a=s.add_parser("record");a.add_argument("output",type=Path);a.add_argument("--seconds",type=float,required=True);a.add_argument("--device",type=int,required=True)
    a.add_argument("--rate",type=int,default=16000)
    args=p.parse_args(argv)
    if args.op=="devices":print(json.dumps(devices(),indent=2))
    else:
        if args.output.suffix.lower()!=".wav" or args.output.exists():p.error("choose a new WAV file")
        publish(args.output,record(args.seconds,args.device,rate=args.rate))
if __name__=="__main__":main()
