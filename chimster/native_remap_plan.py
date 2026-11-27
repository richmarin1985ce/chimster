"""Plan reference remaps without guessing opaque field contents."""
from .native_catalog import CATALOGS
import struct

def plan(profile,signature,parts,source,destination):
    changes=[]
    blockers=[]
    for i,(tag,raw) in enumerate(parts):
        spec=CATALOGS[profile].get((signature,tag))
        if spec is None or len(raw)!=spec.length:
            if source.names!=destination.names:
                blockers.append((i,tag,"opaque"))
            continue
        old=struct.unpack_from("<I",raw,spec.offset)[0]
        try:
            new=destination.encode(source.decode(old))
        except ValueError as exc:
            blockers.append((i,tag,str(exc)))
            continue
        if old!=new:
            changes.append((i,spec.offset,old,new))
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
