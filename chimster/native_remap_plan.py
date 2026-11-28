"""Plan reference remaps without guessing opaque field contents."""
from .native_catalog import references
import struct

def plan(profile,signature,parts,source,destination):
    changes=[]
    blockers=[]
    parts=list(parts)
    try:
        edges,opaque=references(profile,signature,parts,source)
    except (ValueError, KeyError, struct.error) as exc:
        return {"changes":[],"blockers":[(-1,b"",str(exc))],"applicable":False}
    if source.names!=destination.names:
        blockers.extend((i,parts[i][0],"opaque") for i in opaque)
    for i,offset,target,_ in edges:
        tag,raw=parts[i]
        old=struct.unpack_from("<I",raw,offset)[0]
        try:
            new=destination.encode(target)
        except ValueError as exc:
            blockers.append((i,tag,str(exc)))
            continue
        if old!=new:
            changes.append((i,offset,old,new))
    return {"changes":changes,"blockers":blockers,"applicable":not blockers}

def apply(parts,proposal):
    if not proposal["applicable"] or proposal["blockers"]:
        raise ValueError("unsafe remap")
    out=list(parts)
    for i,offset,old,new in proposal["changes"]:
        tag,raw=out[i]
        if struct.unpack_from("<I",raw,offset)[0]!=old:
            raise ValueError("stale remap")
        value=bytearray(raw)
        struct.pack_into("<I",value,offset,new)
        out[i]=(tag,bytes(value))
    return out
