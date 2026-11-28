"""Independent typed templates based on public format documentation.
https://tes5edit.github.io/fopdoc/FalloutNV/Records/MISC.html
"""
import math
import struct
from .native_create import insert

def string(value):
    if not isinstance(value,str) or not value.strip() or "\0" in value:raise ValueError("Invalid text")
    return value.encode("cp1252")+b"\0"

def misc(profile,data,revision,*,editor_id,name,value,weight,bounds,model=None,_signature=b"MISC"):
    if profile!="new-vegas":raise ValueError("Unverified template profile")
    if type(value)!=int or not 0<=value<=2147483647:raise ValueError("Invalid value")
    if type(weight) not in (int,float) or not math.isfinite(weight) or not 0<=weight<=1e6:raise ValueError("Invalid weight")
    bounds=tuple(bounds)
    if len(bounds)!=6 or any(type(v)!=int or not -32768<=v<=32767 for v in bounds) or any(bounds[i]>bounds[i+3] for i in range(3)):raise ValueError("Invalid bounds")
    parts=[(b"EDID",string(editor_id)),(b"OBND",struct.pack("<6h",*bounds)),(b"FULL",string(name))]
    if model is not None:
        path=model.replace("/","\\")
        if ":" in path or path.startswith("\\") or ".." in path.split("\\") or not path.lower().endswith(".nif"):raise ValueError("Invalid relative model path")
        parts.append((b"MODL",string(path)))
    parts.append((b"DATA",struct.pack("<if",value,weight)))
    if _signature not in (b"MISC",b"KEYM"):raise ValueError("Unsupported item type")
    return insert(profile,data,_signature,parts,revision)

def static(profile,data,revision,*,editor_id,bounds,model,passthrough_sound=None):
    """FNV STAT: public fopdoc STAT layout; no game assets bundled."""
    if profile!="new-vegas":raise ValueError("Unverified template profile")
    bounds=tuple(bounds)
    if len(bounds)!=6 or any(type(v)!=int or not -32768<=v<=32767 for v in bounds) or any(bounds[i]>bounds[i+3] for i in range(3)):raise ValueError("Invalid bounds")
    path=model.replace("/","\\")
    if ":" in path or path.startswith("\\") or ".." in path.split("\\") or not path.lower().endswith(".nif"):raise ValueError("Invalid relative model path")
    parts=[(b"EDID",string(editor_id)),(b"OBND",struct.pack("<6h",*bounds)),(b"MODL",string(path))]
    if passthrough_sound is not None:
        if type(passthrough_sound)!=int or not -1<=passthrough_sound<=9:raise ValueError("Invalid passthrough sound")
        parts.append((b"BRUS",struct.pack("<b",passthrough_sound)))
    return insert(profile,data,b"STAT",parts,revision)

def key(profile,data,revision,**properties):
    """KEYM DATA: signed value and float weight, per public fopdoc."""
    return misc(profile,data,revision,_signature=b"KEYM",**properties)
