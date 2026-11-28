"""Ordered, read-only Starfield asset sources and bounded raw LZ4 decoding."""
from pathlib import Path
from .compatibility_asset_lookup import normalize
from .world_models import archive_stamp
from .archive_reader import reader

def lz4_block(data,expected):
    # Pure Python fallback: no external decoder required for Starfield DX10.
    if type(expected) is not int or not 0<=expected<=64*1024*1024:raise ValueError("LZ4 output limit")
    pos=0;out=bytearray()
    def size(n):
        nonlocal pos
        if n==15:
            while True:
                if pos>=len(data):raise ValueError("Truncated LZ4 length")
                b=data[pos];pos+=1;n+=b
                if n>expected:raise ValueError("LZ4 length exceeds output")
                if b!=255:break
        return n
    while pos<len(data):
        token=data[pos];pos+=1
        n=size(token>>4)
        if pos+n>len(data) or len(out)+n>expected:raise ValueError("Invalid LZ4 literal")
        out.extend(data[pos:pos+n]);pos+=n
        if pos==len(data):break
        if pos+2>len(data):raise ValueError("Missing LZ4 offset")
        distance=data[pos]|data[pos+1]<<8;pos+=2
        if not 0<distance<=len(out):raise ValueError("Invalid LZ4 offset")
        count=size(token&15)+4
        if len(out)+count>expected:raise ValueError("LZ4 output overflow")
        # Copy overlapping matches in bounded slices.
        chunk=bytes(out[-distance:])
        times,rem=divmod(count,distance)
        out.extend(chunk*times);out.extend(chunk[:rem])
    if len(out)!=expected:raise ValueError("LZ4 output length mismatch")
    return bytes(out)

class Sources:
    def __init__(self,archives=(),loose=None):
        if len(archives)>64:raise ValueError("Archive count limit")
        self.loose=Path(loose).resolve(strict=True) if loose else None
        if self.loose is not None and not self.loose.is_dir():raise ValueError("Expected Data directory")
        self.archives=[]
        for name in archives:
            path=Path(name).resolve(strict=True)
            if path.suffix.casefold()!=".ba2":raise ValueError("Expected BA2 archive")
            stamp=archive_stamp(path)
            with path.open("rb") as f:
                adapter=reader(f);entries=adapter.directory(f)
            if stamp!=archive_stamp(path):raise ValueError("Archive changed while indexing")
            self.archives.append((path,adapter,entries,stamp))
    def read(self,name,limit=32*1024*1024):
        key=normalize(name)
        if self.loose is not None:
            p=self.loose
            for part in key.split("/"):
                matches=[x for x in p.iterdir() if x.name.casefold()==part] if p.is_dir() else []
                if not matches:p=None;break
                if len(matches)!=1:raise ValueError("Ambiguous loose asset")
                p=matches[0].resolve(strict=True)
                if not p.is_relative_to(self.loose):raise ValueError("Loose asset escapes Data directory")
            if p is not None:
                if not p.is_file() or p.stat().st_size>limit:raise ValueError("Loose asset exceeds limit")
                with p.open("rb") as f:raw=f.read(limit+1)
                if len(raw)>limit:raise ValueError("Loose asset exceeds limit")
                return raw
        for path,adapter,entries,stamp in reversed(self.archives):
            if archive_stamp(path)!=stamp:raise ValueError("Archive changed; reselect")
            if key not in entries:continue
            with path.open("rb") as f:raw=adapter.read(f,entries[key],limit)
            if archive_stamp(path)!=stamp:raise ValueError("Archive changed while reading")
            return raw
        raise FileNotFoundError(key)
