"""Portable PCM conversion; optional host-selected local speech cue backend."""
import io
import math
import struct
import wave
from pathlib import Path

def normalize_pcm(raw):
    from .audio import wav_info
    info=wav_info(raw)
    if info["channels"] not in (1,2) or info["sample_width"] not in (1,2,3,4) or not 8000<=info["sample_rate"]<=96000 or info["duration"]>180:
        raise ValueError("unsupported or oversized PCM input")
    channels,width,rate=info["channels"],info["sample_width"],info["sample_rate"]
    with wave.open(io.BytesIO(raw),"rb") as f:data=f.readframes(info["frames"])
    def sample(frame):
        values=[]
        for c in range(channels):
            i=(frame*channels+c)*width
            v=int.from_bytes(data[i:i+width],"little",signed=width!=1)
            values.append((v-128)*256 if width==1 else v/2**(8*(width-2)))
        return sum(values)/channels
    n=max(1,round(info["frames"]*16000/rate))
    out=bytearray(n*2)
    for i in range(n):
        pos=i*rate/16000
        left=min(int(pos),info["frames"]-1)
        right=min(left+1,info["frames"]-1)
        v=sample(left)+(sample(right)-sample(left))*(pos-int(pos))
        struct.pack_into("<h",out,i*2,max(-32768,min(32767,round(v))))
    buf=io.BytesIO()
    with wave.open(buf,"wb") as f:
        f.setparams((1,2,16000,0,"NONE","not compressed"))
        f.writeframes(out)
    return buf.getvalue()

def lip_preview(source,target,tool,transcript=None):
    from .audio import preview_lips
    if not tool:raise ValueError("host must explicitly configure local Rhubarb executable")
    preview_lips(source,target,tool,transcript)
