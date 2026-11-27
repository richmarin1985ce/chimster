"""Candidate ordered quest stage layouts; retain original fields."""
import struct

def stages(profile,parts):
    if profile not in ("oblivion","fallout3","new-vegas","skyrim","skyrim-se","fallout4"):
        raise ValueError("unsupported quest profile")
    result=[]
    current=None
    for i,(tag,raw) in enumerate(parts):
        if tag==b"INDX" and len(raw)==2:
            current={"index":struct.unpack("<H",raw)[0],"fields":[],"start":i}
            result.append(current)
        elif current is not None:
            current["fields"].append((i,tag,raw))
    return result

def response_text(parts,localized=False,encoding="cp1252"):
    result=[]
    for i,(tag,raw) in enumerate(parts):
        if tag!=b"NAM1":
            continue
        if localized:
            result.append((i,"string-id",struct.unpack("<I",raw)[0]) if len(raw)==4 else (i,"opaque",raw))
        elif raw.endswith(b"\0") and b"\0" not in raw[:-1]:
            result.append((i,"text",raw[:-1].decode(encoding,errors="replace")))
        else:
            result.append((i,"opaque",raw))
    return result
