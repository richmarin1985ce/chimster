"""Inspect NIF version metadata without decoding geometry."""
import re
import struct

def inspect(data):
    end=data.find(b"\n",0,256)
    if end<0:raise ValueError("Missing NIF header")
    line=data[:end].rstrip(b"\r")
    match=re.fullmatch(rb"(NetImmerse|Gamebryo) File Format, Version (\d+)\.(\d+)\.(\d+)\.(\d+)",line)
    if not match:raise ValueError("Unknown NIF header")
    version=tuple(int(x) for x in match.groups()[1:])
    if any(x>255 for x in version):raise ValueError("Invalid version")
    result={"family":match.group(1).decode(),"version":version,"geometry_verified":False}
    if version>=(10,0,1,0):
        if len(data)<end+5:raise ValueError("Truncated binary version")
        binary=struct.unpack_from("<I",data,end+1)[0]
        result["binary_version_matches"]=binary==sum(v<<(24-i*8) for i,v in enumerate(version))
    return result
