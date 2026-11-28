"""BA2 v1 ASCII path hashes.
Format reference: TES5Edit/TES5Edit Core/wbHash.pas and Core/wbBSArchive.pas.
Independent implementation using Python's standard CRC32 primitive.
"""
import zlib
from .compatibility_asset_lookup import normalize

def crc(text):
    raw=text.lower().replace("/",chr(92)).encode("ascii")
    return zlib.crc32(raw,0xffffffff)^0xffffffff

def hashes(path):
    path=normalize(path)
    folder,sep,leaf=path.rpartition("/")
    stem,dot,ext=leaf.rpartition(".")
    if not sep or not folder or not dot or not stem or not 1<=len(ext)<=4:
        raise ValueError("BA2 requires folder, filename and extension")
    return crc(stem),crc(folder)

def prepare(entries):
    seen=set()
    for name,data in entries:
        nh,dh=hashes(name)
        key=(nh,dh,normalize(name).rsplit(".",1)[1])
        if key in seen:raise ValueError("BA2 native hash collision")
        seen.add(key)
        yield name,data,nh,dh
