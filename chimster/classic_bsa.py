"""Experimental BSA 103/104/105 reader for named, sequential folder blocks."""
import struct,zlib
# Format facts: https://bethesda-structs.readthedocs.io/en/latest/bethesda_structs.archive.html
# https://github.com/matiaszanolli/ByroRedux/blob/main/docs/engine/archives.md
from .compatibility_asset_lookup import normalize

def exact(stream,n):
    data=stream.read(n)
    if len(data)!=n:raise ValueError("Truncated BSA")
    return data

def directory(stream):
    stream.seek(0,2);size=stream.tell();stream.seek(0)
    magic,version,offset,flags,folders,files,folder_names,file_names,_=struct.unpack("<4s8I",exact(stream,36))
    if magic!=b"BSA\0" or version not in (103,104,105):raise ValueError("Unsupported BSA version")
    if flags&3!=3 or flags&0x40 or (version==103 and flags&0x100):raise ValueError("Unsupported name configuration")
    stride=24 if version==105 else 16
    if folders>1000000 or files>1000000 or file_names>64*1024*1024 or offset<36 or offset+stride*folders>size:raise ValueError("Invalid directory")
    stream.seek(offset)
    counts=[]
    for _ in range(folders):
        raw=exact(stream,stride);counts.append(struct.unpack_from("<I",raw,8)[0])
    if sum(counts)!=files:raise ValueError("File count mismatch")
    rows=[]
    for count in counts:
        n=exact(stream,1)[0]
        raw=exact(stream,n)
        if not raw.endswith(b"\0"):raise ValueError("Invalid folder name")
        folder=raw[:-1].decode("cp1252")
        for _ in range(count):
            _,length,pos=struct.unpack("<QII",exact(stream,16))
            compressed=bool(flags&4)^bool(length&0x40000000)
            if length&0x80000000:raise ValueError("Unsupported size flag")
            rows.append((folder,pos,length&0x3fffffff,compressed))
    names=exact(stream,file_names).split(b"\0")
    if len(names)!=files+1 or names[-1]:raise ValueError("Invalid file names")
    end=stream.tell();result={}
    for (folder,pos,length,compressed),name in zip(rows,names):
        key=normalize((folder+"/" if folder else "")+name.decode("cp1252"))
        if key in result or pos<end or pos+length>size:raise ValueError("Invalid member")
        result[key]=(pos,length,compressed,version,bool(flags&0x100))
    return result

def read(stream,entry,limit=64*1024*1024):
    pos,length,compressed,version,embedded=entry
    if pos<0 or not 0<=length<=limit:raise ValueError("Invalid member size")
    stream.seek(pos);raw=exact(stream,length)
    if embedded:
        if not raw or 1+raw[0]>len(raw):raise ValueError("Invalid embedded filename")
        raw=raw[1+raw[0]:]
    if not compressed:return raw
    if len(raw)<4:raise ValueError("Missing uncompressed size")
    expected=struct.unpack_from("<I",raw)[0]
    if expected>limit:raise ValueError("Decompression limit")
    if version==105:
        try:from lz4.frame import LZ4FrameDecompressor
        except ImportError as exc:raise ValueError("LZ4 support is not installed") from exc
        dec=LZ4FrameDecompressor();out=dec.decompress(raw[4:],max_length=expected+1)
        if len(out)!=expected or not dec.eof or dec.unused_data:raise ValueError("Invalid LZ4 member")
        return out
    dec=zlib.decompressobj();out=dec.decompress(raw[4:],expected+1)
    if len(out)!=expected or not dec.eof or dec.unused_data or dec.unconsumed_tail:raise ValueError("Invalid compressed member")
    return out
