"""Exact flat generated record layouts eligible for master remapping.
Opaque templates (NPC_, RACE, WEAP, ARMO, PACK, MGEF) deliberately excluded."""
import re,struct
from .fnv_records import text
from .fnv_patch import sub
PATTERNS={
 b"FACT":r"EDIDFULL(?:XNAM)*DATA(?:RNAMMNAMFNAM)*(?:WMI1)?",
 b"REPU":r"EDIDFULLDATA",b"VTYP":r"EDIDDNAM",
 b"CLAS":r"EDIDFULLDESCDATAATTR",
 b"KEYM":r"EDIDOBNDFULLMODLICONMICODATA",
 b"CONT":r"EDIDOBNDFULLMODL(?:CNTO)*DATA",
 b"LVLI":r"EDIDOBNDLVLDLVLFLVLG(?:LVLO)+",
 b"LVLN":r"EDIDOBNDLVLDLVLF(?:LVLO)+",
 b"AMMO":r"EDIDOBNDFULLMODLDATADAT2(?:ONAM)?(?:QNAM)?",
 b"ECZN":r"EDIDDATA",
 b"SPEL":r"EDIDFULLSPIT(?:EFIDEFIT)+",
 b"ALCH":r"EDIDOBNDFULLMODLETYPDATAENIT(?:EFIDEFIT)+",
 b"PERK":r"EDIDFULLDESCDATA(?:PRKEDATAPRKF)+",
}
STRINGS={b"EDID",b"FULL",b"DESC",b"MODL",b"ICON",b"MICO",b"ONAM",b"QNAM",b"MNAM",b"FNAM"}
LENGTHS={
 b"FACT":{b"XNAM":12,b"DATA":4,b"RNAM":4,b"WMI1":4},
 b"REPU":{b"DATA":4},b"VTYP":{b"DNAM":1},b"CLAS":{b"DATA":28,b"ATTR":7},
 b"KEYM":{b"OBND":12,b"DATA":8},b"CONT":{b"OBND":12,b"CNTO":8,b"DATA":5},
 b"LVLI":{b"OBND":12,b"LVLD":1,b"LVLF":1,b"LVLG":4,b"LVLO":12},
 b"LVLN":{b"OBND":12,b"LVLD":1,b"LVLF":1,b"LVLO":12},
 b"AMMO":{b"OBND":12,b"DATA":13,b"DAT2":20},b"ECZN":{b"DATA":8},
 b"SPEL":{b"SPIT":16,b"EFID":4,b"EFIT":20},b"ALCH":{b"OBND":12,b"ETYP":4,b"DATA":4,b"ENIT":20,b"EFID":4,b"EFIT":20},
 b"PERK":{b"PRKE":3,b"PRKF":0},
}
OFFSETS={
 b"FACT":{b"XNAM":[0],b"WMI1":[0]},b"CONT":{b"CNTO":[0]},
 b"LVLI":{b"LVLG":[0],b"LVLO":[4]},b"LVLN":{b"LVLO":[4]},
 b"AMMO":{b"DAT2":[4,12]},b"ECZN":{b"DATA":[0]},
 b"SPEL":{b"EFID":[0]},b"ALCH":{b"ENIT":[8,16],b"EFID":[0]},
}
def rewrite(sig,parts,remap):
    tags="".join(k.decode("ascii") for k,_ in parts)
    if sig not in PATTERNS or re.fullmatch(PATTERNS[sig],tags) is None:raise ValueError("unknown generated record layout")
    result=[];changed=0;perk=None
    for k,v in parts:
        offsets=OFFSETS.get(sig,{}).get(k,[])
        if sig==b"PERK" and k==b"PRKE":
            if len(v)!=3 or v[0] not in (0,1):raise ValueError("unsupported perk effect")
            perk=v[0]
        if sig==b"PERK" and k==b"DATA":
            length=5 if perk is None else 8 if perk==0 else 4
            if len(v)!=length:raise ValueError("invalid perk DATA")
            if perk is not None:offsets=[0]
        elif k in LENGTHS[sig]:
            if len(v)!=LENGTHS[sig][k]:raise ValueError("invalid "+k.decode()+" size")
        elif k in STRINGS:text(v)
        else:raise ValueError("unknown field")
        raw=bytearray(v)
        for off in offsets:
            old=struct.unpack_from("<I",raw,off)[0];new=remap(old)
            struct.pack_into("<I",raw,off,new);changed+=old!=new
        result.append(sub(k,bytes(raw)))
    return b"".join(result),changed
