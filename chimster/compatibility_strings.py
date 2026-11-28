"""Read-only STRINGS/DLSTRINGS/ILSTRINGS parsing with explicit encoding."""
import struct

def parse(data,kind,encoding="utf-8"):
    kind=kind.upper().lstrip(".")
    if kind not in ("STRINGS","DLSTRINGS","ILSTRINGS"):raise ValueError("Unsupported table")
    if len(data)<8:raise ValueError("Truncated header")
    count,size=struct.unpack_from("<II",data)
    start=8+count*8
    if start+size!=len(data):raise ValueError("Invalid table extent")
    result={}
    for i in range(count):
        key,offset=struct.unpack_from("<II",data,8+i*8)
        if key in result or offset>=size:raise ValueError("Invalid directory entry")
        pos=start+offset
        if kind=="STRINGS":
            end=data.find(b"\0",pos)
            if end<0:raise ValueError("Unterminated string")
            raw=data[pos:end]
        else:
            if pos+4>len(data):raise ValueError("Truncated string length")
            length=struct.unpack_from("<I",data,pos)[0]
            pos+=4
            if length<1 or pos+length>len(data) or data[pos+length-1]!=0:raise ValueError("Invalid string extent")
            raw=data[pos:pos+length-1]
        if b"\0" in raw:raise ValueError("Embedded null")
        result[key]=raw.decode(encoding)
    return result
