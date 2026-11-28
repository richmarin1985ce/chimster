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


def encode(entries,kind,encoding="utf-8"):
    """Build a standalone native string table; preserve every existing string ID."""
    kind=kind.upper().lstrip(".")
    if kind not in ("STRINGS","DLSTRINGS","ILSTRINGS"):raise ValueError("Unsupported table")
    if not isinstance(entries,dict) or len(entries)>1000000:raise ValueError("Invalid entries")
    if any(type(k)!=int or not 0<=k<=0xffffffff for k in entries):raise ValueError("Invalid string ID")
    directory=[];payload=bytearray()
    for key in sorted(entries):
        value=entries[key]
        if not isinstance(value,str) or "\0" in value:raise ValueError("Invalid string value")
        raw=value.encode(encoding)+b"\0"
        body=raw if kind=="STRINGS" else struct.pack("<I",len(raw))+raw
        if len(payload)+len(body)>128*1024*1024:raise ValueError("String table exceeds limit")
        directory.append(struct.pack("<II",key,len(payload)));payload.extend(body)
    data=struct.pack("<II",len(entries),len(payload))+b"".join(directory)+payload
    if parse(data,kind,encoding)!=entries:raise ValueError("String table verification failed")
    return data

def edit(data,kind,changes,expected_revision,encoding="utf-8"):
    """Revise existing IDs only; no implicit plugin or string-ID allocation."""
    import hashlib
    if hashlib.sha256(data).hexdigest()!=expected_revision:raise ValueError("Stale string table")
    entries=parse(data,kind,encoding)
    if not isinstance(changes,dict) or not changes or any(type(k)!=int or k not in entries for k in changes):
        raise ValueError("Unknown string ID")
    if all(entries[k]==v for k,v in changes.items()):return data
    entries.update(changes)
    return encode(entries,kind,encoding)
