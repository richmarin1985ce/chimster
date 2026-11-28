"""Exact generated script-free FNV quest layouts, not arbitrary native quests."""
import re,struct,math
from .fnv_records import text
from .fnv_patch import sub

EMPTY=r"SCHRSCDASCTX"
PATTERNS={
    b"QUST":r"EDID(?:SCRI)?FULLDATA(?:CTDA)*(?:INDXQSDT(?:CTDA)*CNAM"+EMPTY+r"(?:NAM0)?)+(?:QOBJNNAM(?:QSTA(?:CTDA)*)*)*",
    b"DIAL":r"EDIDQSTIFULLPNAMDATA",
    b"INFO":r"DATAQSTITPICPNAM(?:TRDTNAM1NAM2(?:SNAM)?(?:LNAM)?)+(?:CTDA)*(?:TCLT)*(?:TCLF)*"+EMPTY+r"NEXT"+EMPTY+r"(?:RNAM)?(?:ANAM)?(?:KNAM)?(?:DNAM)?",
}
LINKS={
    b"QUST":{b"SCRI":("SCPT",),b"NAM0":("QUST",),b"QSTA":("REFR","ACHR","ACRE","PGRE","PMIS")},
    b"DIAL":{b"QSTI":("QUST",)},
    b"INFO":{b"QSTI":("QUST",),b"TPIC":("DIAL",),b"PNAM":("INFO",),b"SNAM":("IDLE",),b"LNAM":("IDLE",),b"TCLT":("DIAL",),b"TCLF":("DIAL",),b"ANAM":("NPC_","CREA"),b"KNAM":("AVIF","PERK")},
}
SIZES={b"QUST":{b"DATA":8,b"INDX":2,b"QSDT":1,b"QOBJ":4,b"QSTA":8},
       b"DIAL":{b"DATA":2,b"PNAM":4},
       b"INFO":{b"DATA":4,b"TRDT":24,b"DNAM":4}}
STRINGS={b"EDID",b"FULL",b"CNAM",b"NNAM",b"NAM1",b"NAM2",b"RNAM"}
CONDITIONS={59:("QUST",),71:("FACT",),72:("NPC_","CREA"),574:("REPU",)}

def fields(signature,parts):
    """Validate the whole layout and yield (field index, offset, target types)."""
    parts=list(parts)
    if not re.fullmatch(PATTERNS[signature],"".join(k.decode("ascii") for k,_ in parts)):
        raise ValueError("unsupported quest layout")
    result=[]
    for i,(tag,raw) in enumerate(parts):
        if tag in (b"SCHR",b"SCDA",b"SCTX",b"NEXT"):
            if raw!=(bytes(20) if tag==b"SCHR" else b""):
                raise ValueError("nonempty script or unsupported script header")
            continue
        kinds=LINKS[signature].get(tag)
        size=SIZES[signature].get(tag)
        if kinds:
            if len(raw)!=(size if size is not None else 4):raise ValueError("invalid quest link size")
            if not struct.unpack_from("<I",raw)[0] and not (signature==b"INFO" and tag==b"PNAM"):
                raise ValueError("null required quest link")
            result.append((i,0,kinds))
        elif tag==b"CTDA":
            if len(raw)!=28:raise ValueError("invalid condition size")
            op,value,func,ref,param,run_on,run_ref=struct.unpack("<B3xfIIIII",raw)
            if func not in CONDITIONS or run_on or run_ref or not ref or not math.isfinite(value):
                raise ValueError("unsupported condition function or run-on")
            if func==574:
                if op not in (0,32,64,96,128,160) or not 0<=value<=1 or param not in (0,1):
                    raise ValueError("unsupported reputation condition")
            elif op or value not in (0.,1.) or (func==59 and param>255) or (func!=59 and param):
                raise ValueError("unsupported generated condition")
            result.append((i,12,CONDITIONS[func]))
        elif size is not None:
            if len(raw)!=size:raise ValueError("invalid quest field size")
            if tag==b"TRDT":result.append((i,16,("SOUN",)))
        elif tag in STRINGS:text(raw)
        else:raise ValueError("unknown quest field")
    return result

def rewrite_quest(signature,parts,remap):
    parts=list(parts);changed=0
    for i,offset,kinds in fields(signature,parts):
        tag,raw=parts[i];old=struct.unpack_from("<I",raw,offset)[0]
        if old:
            new=remap(old,kinds);changed+=old!=new
            raw=raw[:offset]+struct.pack("<I",new)+raw[offset+4:]
            parts[i]=(tag,raw)
    return b"".join(sub(tag,raw) for tag,raw in parts),changed
