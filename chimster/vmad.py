"""Bounded Skyrim VMAD v5 codec. Fallout 4 structs and fragment tails are opaque.

Read basic scripts/properties; edit existing scalar values without reserializing
other fields. No FormID rebasing, alias manipulation, or runtime certification.
"""
import hashlib
import math
import struct
from pathlib import Path

GAMES={"skyrim","skyrimse","skyrimae","skyrimvr"}
TYPES={1:"object",2:"string",3:"int",4:"float",5:"bool",
       11:"object[]",12:"string[]",13:"int[]",14:"float[]",15:"bool[]"}
MAX=8*1024*1024

class Reader:
    def __init__(self,data):
        if not isinstance(data,bytes) or len(data)>MAX:raise ValueError("invalid VMAD size")
        self.data=data;self.pos=0
    def take(self,n):
        if n<0 or self.pos+n>len(self.data):raise ValueError("truncated VMAD")
        b=self.data[self.pos:self.pos+n];self.pos+=n;return b
    def unpack(self,fmt):
        return struct.unpack("<"+fmt,self.take(struct.calcsize("<"+fmt)))[0]
    def string(self):
        return self.take(self.unpack("H")).decode("utf-8",errors="strict")

def parse(data,game):
    if game not in GAMES:raise ValueError("only Skyrim-family VMAD v5 supported")
    r=Reader(data)
    version,fmt,count=(r.unpack("H") for _ in range(3))
    if version!=5 or fmt not in (1,2):raise ValueError("unsupported VMAD version/object format")
    if count>4096:raise ValueError("script count limit")
    def scalar(typ):
        if typ==1:
            raw=r.take(8)
            # Keep object byte order and alias metadata intact. Disk IDs are
            # not load-order IDs, and no form resolution is attempted here.
            return {"raw_hex":raw.hex(),"disk_form_id":struct.unpack_from("<I",raw,0 if fmt==1 else 4)[0]}
        if typ==2:return r.string()
        if typ==3:return r.unpack("i")
        if typ==4:
            v=r.unpack("f")
            return v if math.isfinite(v) else {"nonfinite":True}
        if typ==5:
            v=r.unpack("B")
            if v not in (0,1):raise ValueError("invalid bool property")
            return bool(v)
        raise ValueError("unknown VMAD type")
    scripts=[];seen=set()
    for _ in range(count):
        name=r.string();status=r.unpack("B");n=r.unpack("H")
        if not name or name.casefold() in seen or n>8192:raise ValueError("ambiguous script or property count limit")
        seen.add(name.casefold());props=[];names=set()
        for _ in range(n):
            pn=r.string();typ=r.unpack("B");flags=r.unpack("B");start=r.pos
            if not pn or pn.casefold() in names or typ not in TYPES:raise ValueError("ambiguous or unsupported property")
            names.add(pn.casefold())
            if typ>=11:
                size=r.unpack("I")
                if size>65536:raise ValueError("array limit")
                value=[scalar(typ-10) for _ in range(size)]
            else:value=scalar(typ)
            props.append({"name":pn,"type":TYPES[typ],"type_id":typ,"status":flags,
                          "value":value,"start":start,"end":r.pos})
        scripts.append({"name":name,"status":status,"properties":props})
    return {"version":version,"object_format":fmt,"scripts":scripts,
            "tail_offset":r.pos,"opaque_tail_bytes":len(data)-r.pos,
            "sha256":hashlib.sha256(data).hexdigest(),
            "scope":"base script/property table only; fragment/alias tail opaque"}

def encode_scalar(typ,value):
    if typ==2:
        if not isinstance(value,str) or "\0" in value:raise ValueError("expected string without NUL")
        raw=value.encode("utf-8")
        if len(raw)>65535:raise ValueError("string too long")
        return struct.pack("<H",len(raw))+raw
    if typ==3:
        if type(value) is not int or not -(2**31)<=value<2**31:raise ValueError("expected signed 32-bit integer")
        return struct.pack("<i",value)
    if typ==4:
        if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>3.402823466e38:
            raise ValueError("expected finite float32")
        return struct.pack("<f",value)
    if typ==5:
        if type(value) is not bool:raise ValueError("expected boolean")
        return bytes([int(value)])
    raise ValueError("only existing scalar string/int/float/bool properties are editable")

def edit(data,game,script,property_name,value,expected_sha256):
    report=parse(data,game)
    if report["sha256"]!=expected_sha256:raise ValueError("stale VMAD snapshot")
    if report["opaque_tail_bytes"]:raise ValueError("fragment/alias tail requires specialized writer")
    matches=[p for s in report["scripts"] if s["name"].casefold()==script.casefold()
             for p in s["properties"] if p["name"].casefold()==property_name.casefold()]
    if len(matches)!=1:raise ValueError("property not found or ambiguous")
    p=matches[0]
    raw=encode_scalar(p["type_id"],value)
    result=data[:p["start"]]+raw+data[p["end"]:]
    parse(result,game)
    return result

def read_payload(path):
    p=Path(path)
    if p.stat().st_size>MAX:raise ValueError("VMAD payload too large")
    return p.read_bytes()

def inspect_file(path,game):
    return parse(read_payload(path),game)

def edit_file(path,output,game,script,property_name,value,expected_sha256):
    p=Path(path);q=Path(output)
    raw=read_payload(p)
    result=edit(raw,game,script,property_name,value,expected_sha256)
    if p.read_bytes()!=raw:raise ValueError("source changed")
    with q.open("xb") as stream:stream.write(result)
    return {"output":str(q),**parse(result,game)}
