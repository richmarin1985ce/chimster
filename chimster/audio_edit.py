"""Non-destructive PCM editing and preview-only mouth cue timing."""
from __future__ import annotations
import io
import math
import json
from pathlib import Path
import shutil
import struct
import subprocess
import wave
from .audio import publish, validate_cues

MAX_BYTES = 128 * 1024 * 1024

class Clip:
    def __init__(self, data: bytes):
        if len(data) > MAX_BYTES:
            raise ValueError("audio exceeds editor size limit")
        with wave.open(io.BytesIO(data), "rb") as f:
            self.channels, self.rate = f.getnchannels(), f.getframerate()
            self.frames = f.getnframes()
            if f.getsampwidth() != 2 or self.channels not in (1, 2) or not self.frames:
                raise ValueError("editor requires nonempty mono/stereo PCM16 WAV")
            self.data = f.readframes(self.frames)
        if len(self.data) != self.frames * self.channels * 2:
            raise ValueError("truncated PCM")
        self.duration = self.frames / self.rate

    @classmethod
    def open(cls, path):
        p = Path(path)
        if p.stat().st_size > MAX_BYTES:
            raise ValueError("audio exceeds editor size limit")
        return cls(p.read_bytes())

    def envelope(self, bins=800):
        if not 1 <= bins <= 8192:
            raise ValueError("invalid waveform resolution")
        bins = min(bins, self.frames)
        result = []
        stride = self.channels * 2
        for i in range(bins):
            a, b = i * self.frames // bins, (i + 1) * self.frames // bins
            samples = [v[0] for v in struct.iter_unpack("<h", self.data[a*stride:b*stride])]
            result.append((min(samples)/32768, max(samples)/32768))
        return result

    def selection(self, start, end):
        if not math.isfinite(start) or not math.isfinite(end) or not 0 <= start < end <= self.duration:
            raise ValueError("invalid selection")
        a, b = round(start*self.rate), round(end*self.rate)
        if a >= b:
            raise ValueError("selection shorter than one sample")
        return a, b

    def edited(self, start=0, end=None, *, gain_db=0, fade_in=0, fade_out=0):
        end = self.duration if end is None else end
        a, b = self.selection(start, end)
        if not all(math.isfinite(x) for x in (gain_db,fade_in,fade_out)) or not -60 <= gain_db <= 24 or min(fade_in,fade_out) < 0 or fade_in+fade_out > (b-a)/self.rate:
            raise ValueError("invalid gain or fades")
        stride = self.channels * 2
        data = bytearray(self.data[a*stride:b*stride])
        if gain_db or fade_in or fade_out:
            gain = 10 ** (gain_db/20)
            fi, fo = round(fade_in*self.rate), round(fade_out*self.rate)
            for i in range(b-a):
                scale = gain
                if fi: scale *= min(1, i/fi)
                if fo: scale *= min(1, (b-a-1-i)/fo)
                for c in range(self.channels):
                    pos = i*stride+c*2
                    v = struct.unpack_from("<h",data,pos)[0]
                    struct.pack_into("<h",data,pos,max(-32768,min(32767,round(v*scale))))
        out = io.BytesIO()
        with wave.open(out,"wb") as f:
            f.setnchannels(self.channels); f.setsampwidth(2); f.setframerate(self.rate)
            f.writeframes(data)
        return out.getvalue()

    def export(self, path, *args, **kwargs):
        if Path(path).suffix.lower() != ".wav":
            raise ValueError("expected .wav destination")
        publish(Path(path), self.edited(*args, **kwargs))

def read_cues(path, duration):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_cues(obj,duration)
    return obj

def edit_cue(obj, index, start, end, shape, duration):
    rows = [dict(c) for c in obj["mouthCues"]]
    if not 0 <= index < len(rows):
        raise ValueError("select a cue")
    rows[index] = {"start":float(start),"end":float(end),"value":shape}
    result = {**obj,"mouthCues":rows}
    validate_cues(result,duration)
    return result

def trim_cues(obj, start, end, duration):
    validate_cues(obj,duration)
    if not 0 <= start < end <= duration:
        raise ValueError("invalid trim")
    rows = []
    for c in obj["mouthCues"]:
        a,b=max(start,float(c["start"])),min(end,float(c["end"]))
        if b>a: rows.append({"start":a-start,"end":b-start,"value":c["value"]})
    result = {**obj,"metadata":{**obj.get("metadata",{}),"duration":end-start},"mouthCues":rows}
    validate_cues(result,end-start)
    return result

def export_cues(path,obj,duration):
    if Path(path).suffix.lower() != ".json":
        raise ValueError("preview cues are JSON, never native LIP")
    validate_cues(obj,duration)
    publish(Path(path),json.dumps(obj,indent=2).encode("utf-8"))

def play(path, start=0, end=None, executable=None):
    path = Path(path).resolve(strict=True)
    clip = Clip.open(path)
    end = clip.duration if end is None else end
    clip.selection(start,end)
    player = shutil.which(executable or "ffplay")
    if not player:
        raise ValueError("install FFplay or select its executable")
    return subprocess.Popen([player,"-nodisp","-autoexit","-loglevel","error",
        "-ss",str(start),"-t",str(end-start),str(path)],stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,shell=False)
