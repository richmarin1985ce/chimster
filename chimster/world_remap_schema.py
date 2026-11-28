"""Exact Chimster-generated FNV world subset, not a general retail schema."""
import re,struct,math
from .fnv_records import text
from .fnv_patch import sub

PATTERNS={
    b"WRLD":r"EDIDFULLPNAMDNAMONAMDATANAM0NAM9NNAMXNAM",
    b"CELL":r"(?:DATAXCLC|EDIDFULLDATA)",
    b"LAND":r"DATAVNMLVHGTVCLR(?:BTXT)*(?:ATXTVTXT)*",
    b"REFR":r"NAME(?:XTEL)?(?:XLKR)?XSCLDATA",
    b"DOOR":r"EDIDOBNDFULLMODLFNAM",
    b"TXST":r"EDIDOBNDTX00TX01DNAM",
    b"LTEX":r"EDIDICONMICOTNAMHNAMSNAM",
    b"BOOK":r"EDIDOBNDFULL(?:MODL)?DESCDATA",
    b"NOTE":r"EDIDOBNDFULL(?:MODL)?DATATNAM",
}
LENGTHS={
    b"WRLD":{b"PNAM":2,b"DNAM":8,b"ONAM":12,b"DATA":1,b"NAM0":8,b"NAM9":8,b"NNAM":1,b"XNAM":1},
    b"CELL":{b"DATA":1,b"XCLC":12},
    b"LAND":{b"DATA":4,b"VNML":3267,b"VHGT":1096,b"VCLR":3267,b"BTXT":8,b"ATXT":8},
    b"REFR":{b"NAME":4,b"XTEL":32,b"XLKR":4,b"XSCL":4,b"DATA":24},
    b"DOOR":{b"OBND":12,b"FNAM":1},
    b"TXST":{b"OBND":12,b"DNAM":2},
    b"LTEX":{b"TNAM":4,b"HNAM":3,b"SNAM":1},
    b"BOOK":{b"OBND":12,b"DATA":10},
    b"NOTE":{b"OBND":12,b"DATA":1},
}
LINKS={b"LAND":{b"BTXT":("LTEX",),b"ATXT":("LTEX",)},
       b"REFR":{b"NAME":("STAT","BOOK","NOTE","DOOR"),b"XTEL":("REFR",),b"XLKR":("REFR","ACHR","ACRE","PGRE","PMIS")},b"LTEX":{b"TNAM":("TXST",)}}
STRINGS={b"EDID",b"FULL",b"MODL",b"DESC",b"TX00",b"TX01",b"ICON",b"MICO",b"TNAM"}

def rewrite_world(signature,parts,remap):
    tags="".join(tag.decode("ascii") for tag,_ in parts)
    if not re.fullmatch(PATTERNS[signature],tags):
        raise ValueError("unknown generated world layout")
    if signature==b"CELL":
        values=dict(parts)
        if values[b"DATA"]!=(b"\x01" if tags=="EDIDFULLDATA" else b"\0"):
            raise ValueError("unsupported cell flags")
    output=[];changed=0
    for tag,raw in parts:
        length=LENGTHS[signature].get(tag)
        if length is not None:
            if len(raw)!=length:raise ValueError("invalid world field size")
        elif tag==b"VTXT" and signature==b"LAND":
            if len(raw)%8:raise ValueError("invalid VTXT size")
        elif tag in STRINGS:
            text(raw)
        else:raise ValueError("unknown world field")
        if signature==b"NOTE" and tag==b"DATA" and raw!=b"\x01":
            raise ValueError("unsupported non-text note")
        if signature==b"WRLD" and tag in (b"NNAM",b"XNAM") and raw!=b"\0":
            raise ValueError("unsupported world field value")
        if signature==b"DOOR" and tag==b"FNAM" and raw[0]&~0x1e:raise ValueError("unsupported door flags")
        if tag==b"XTEL" and signature==b"REFR":
            values=struct.unpack("<I6fI",raw)
            if not all(math.isfinite(v) for v in values[1:7]) or values[-1]&~1:raise ValueError("invalid teleport destination")
        kinds=LINKS.get(signature,{}).get(tag)
        if kinds:
            old=struct.unpack_from("<I",raw)[0]
            if not old:raise ValueError("null world reference")
            new=remap(old,kinds)
            raw=struct.pack("<I",new)+raw[4:]
            changed+=old!=new
        output.append(sub(tag,raw))
    return b"".join(output),changed

def fields(signature,parts):
    """Expose the exact same validated references to the graph/editor."""
    parts=list(parts)
    rewrite_world(signature,parts,lambda raw,kinds:raw)
    return [(i,0,LINKS[signature][tag]) for i,(tag,raw) in enumerate(parts)
            if tag in LINKS.get(signature,{})]
