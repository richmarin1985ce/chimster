"""Independent legacy SpeedTree SPT token reader and lossless scalar editor.

Format facts: documented legacy 4.x token layout (spttools FORMAT), not its
implementation. Unknown tokens stop the walk; never scan/resync through payloads.
The same signature can occur in different game variants.
"""
import struct,hashlib
from math import isfinite
from pathlib import PurePosixPath

# Widths in bytes, or length-prefixed strings/UV quads. Unknown layouts fail closed.
MARKERS={1001,1002,1003,1004,1005,1007,1008,1009,1010,1011,1012,1015,1016,1017,7000,7001,9005,9006,40006,40007,40008,50002,50003,60002,60003,60004,60005,60009,71000,71002,71005,71011,71014,71015,72000,72004,73002,73003,26002,26003}
for base in (8000,9000,10000,11000,12000,13000,14000,15000,16000,18000,19000,20000,25000,26000,27000,28000,29000,30000,40000,50000,60000,70000,73000,74000,75000):MARKERS.update((base,base+1))
STRINGS={1000,2000,4003,13005,14002,18005,20002,26013,26014,26018,26019,26020,26022,60006,71003,*range(70002,70009),*range(6000,6008),6017}
BYTES={2002,3003,3006,3009,4000,5006,6015,6016,13007,15002,20003,20004,22000,25007,26009,26023,27002,28002,50006,50007,50009,50011,50012,50018,72001,75004}
VECTORS={4001:3,4004:3,4005:3,4006:3,5000:3,5001:3,5002:3,5003:3,5004:3,8003:13,8005:13,8009:13,12002:4,12003:5,12004:6,18002:3,18003:3,18004:3,20005:8,71006:3,71007:3,71008:3,71009:3,71010:2}
WORDS={1006,1014,2001,2003,2004,2005,2006,2007,3000,3001,3002,3004,3005,3007,3008,3010,4002,4007,5005,6008,6009,*range(6010,6015),8002,8004,8006,8007,8008,9002,9003,9004,*range(9007,9015),11002,13002,13003,13004,13006,13008,*range(13009,13014),*range(14003,14009),15003,*range(16002,16015),19002,21000,21001,23002,23003,*range(25002,25007),*range(26004,26009),26010,26011,26012,26015,26016,26017,26021,*range(27003,27007),28003,28004,29002,*range(30002,30010),*range(40002,40006),50004,50005,50008,50010,*range(50013,50018),60007,60008,71001,71004,71012,71013,72003,72005,72006,73004,73005,73006,74002,75002,75003,75005}
UV_ARRAYS={10002,10003,10004}
FLOAT_FIELDS={2001:"far_distance",2003:"near_distance",2006:"size",2007:"size_variance",21000:"leaf_rock",21001:"leaf_rustle",74002:"orientation"}
INT_FIELDS={2005:"seed",1014:"levels",1006:"leaf_maps"}

def parse(raw):
    if not 8<=len(raw)<=64*1024*1024:raise ValueError("SPT size limit")
    pos=0;tokens=[];fields={};textures=[];billboards=[];unknown=None
    def take(n):
        nonlocal pos
        if n<0 or pos+n>len(raw):raise ValueError("Truncated SPT payload")
        start=pos;pos+=n;return raw[start:pos]
    def word():return struct.unpack("<I",take(4))[0]
    while pos<len(raw):
        if len(tokens)>=250000:raise ValueError("SPT token budget")
        offset=pos;tag=word();start=pos
        if not tokens and tag!=1000:raise ValueError("Missing SPT version token")
        if tag in STRINGS:
            n=word()
            if n>1048576:raise ValueError("SPT string budget")
            data=take(n);value=data.rstrip(b"\0").decode("latin-1")
            if tag==1000:
                if not value.startswith("__IdvSpt_"):raise ValueError("Invalid SPT signature")
                fields["signature"]=value
            elif tag in (2000,4003,14002,18005,20002,60006,70002,70003,70004,70005,70006,70007,70008):
                if value:textures.append({"tag":tag,"value":value})
        elif tag in UV_ARRAYS:
            n=word()
            if n>4096:raise ValueError("SPT UV array budget")
            value=list(struct.iter_unpack("<8f",take(n*32)))
            if tag==10003:billboards.extend(value)
        elif tag in MARKERS:value=None
        elif tag in BYTES:value=take(1)[0]
        elif tag in VECTORS:value=struct.unpack("<"+"f"*VECTORS[tag],take(4*VECTORS[tag]))
        elif tag in WORDS:
            data=take(4)
            value=struct.unpack("<f" if tag in FLOAT_FIELDS else "<I",data)[0]
            if tag in FLOAT_FIELDS:
                if not isfinite(value):raise ValueError("Nonfinite SPT scalar")
                fields.setdefault(FLOAT_FIELDS[tag],value)
            if tag in INT_FIELDS:fields.setdefault(INT_FIELDS[tag],value)
        else:
            unknown={"tag":tag,"offset":offset};pos=offset;break
        tokens.append({"tag":tag,"offset":offset,"payload":start,"end":pos})
    if not tokens or "signature" not in fields:raise ValueError("Missing SPT signature")
    return {"fields":fields,"textures":textures,"billboard_uvs":billboards,"tokens":tokens,
            "unknown":unknown,"parsed_bytes":pos,"bytes":len(raw),"complete":unknown is None and pos==len(raw),
            "sha256":hashlib.sha256(raw).hexdigest()}

def edit_scalars(raw,changes):
    """Only edit uniquely identified, validated scalar payloads. Preserve all other bytes."""
    before=parse(raw)
    if not before["complete"]:raise ValueError("Cannot edit partially parsed SPT")
    allowed={"seed":2005,"size":2006,"size_variance":2007,"near_distance":2003,"far_distance":2001}
    out=bytearray(raw)
    for name,value in changes.items():
        if name not in allowed:raise ValueError("Unsupported scalar "+name)
        tag=allowed[name];hits=[t for t in before["tokens"] if t["tag"]==tag]
        if len(hits)!=1:raise ValueError("Missing or ambiguous scalar "+name)
        if name=="seed":
            if type(value)!=int or not 0<=value<=0xffffffff:raise ValueError("Invalid seed")
            data=struct.pack("<I",value)
        else:
            if not isinstance(value,(int,float)) or not isfinite(value) or not 0<=value<=1e8 or name=="size" and value==0:raise ValueError("Invalid scalar "+name)
            data=struct.pack("<f",value)
        out[hits[0]["payload"]:hits[0]["end"]]=data
    after=parse(out)
    if not after["complete"] or after["tokens"]!=before["tokens"]:raise ValueError("SPT structure changed")
    f=after["fields"]
    if "near_distance" in f and "far_distance" in f and f["near_distance"]>f["far_distance"]:raise ValueError("Invalid LOD distance order")
    return bytes(out)

def model_path(path):
    path=path.replace("\\","/")
    if not path.lower().startswith("trees/"):path="trees/"+path
    if not path.lower().endswith(".spt") or any(not p or p in (".","..") or ":" in p or "\0" in p for p in path.split("/")):raise ValueError("Unsafe SPT path")
    return path

def billboard_paths(path):
    stem=PurePosixPath(model_path(path)).stem
    return (f"textures/trees/billboards/{stem}.dds",f"trees/billboards/{stem}.dds")
