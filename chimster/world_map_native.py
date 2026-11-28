"""Read-only Skyrim world map adapter; preserve native payloads."""
import struct
from math import isfinite
from .native_parser import parse,subrecords

def inspect(profile,data):
    profile={"skyrimse":"skyrim-se"}.get(profile,profile)
    if profile not in ("skyrim","skyrim-se"):raise ValueError("Unsupported profile")
    worlds=[];markers=[]
    def walk(nodes,groups=()):
        for node in nodes:
            if node.signature==b"GRUP":
                walk(node.children,groups+((node.header[8:12].hex(),struct.unpack_from("<i",node.header,12)[0]),))
                continue
            if node.signature not in (b"WRLD",b"REFR"):continue
            parts=list(subrecords(profile,node))
            flags,fid=struct.unpack_from("<II",node.header,8)
            if flags&0x20:continue
            if node.signature==b"REFR":
                if not any(k==b"XMRK" for k,v in parts):continue
                markers.append({"form_id_raw":fid,"groups":groups,"fields":[(k.decode("ascii"),v.hex()) for k,v in parts],"status":"raw marker including localized name and flags"})
                continue
            row={"form_id_raw":fid,"groups":groups,"issues":[]}
            for tag,raw in parts:
                if tag==b"MODL":
                    if raw.endswith(b"\0") and b"\0" not in raw[:-1]:row["cloud_model"]=raw[:-1].decode("cp1252")
                    else:row["issues"].append("Invalid cloud model string")
                elif tag==b"MNAM":
                    if len(raw) in (16,24,28):
                        row["map_dimensions_cells_raw"]=struct.unpack_from("<2i4h",raw)
                        camera=struct.unpack("<"+"f"*((len(raw)-16)//4),raw[16:])
                        if all(isfinite(v) for v in camera):row["map_camera_raw"]=camera
                        else:row["issues"].append("Nonfinite map camera")
                    else:row["issues"].append("Unknown MNAM size")
                elif tag==b"ONAM" and len(raw)==16:
                    v=struct.unpack("<4f",raw)
                    if all(isfinite(x) for x in v):row["map_scale_offset"]=v
                elif tag==b"MHDT":row["height_data_raw"]=raw.hex()
            worlds.append(row)
    walk(parse(profile,data))
    return {"worldspaces":worlds,"markers":markers}

def cloud_model_field(path):
    """Build a MODL payload only; caller must preserve model metadata and record identity."""
    path=path.replace("/","\\")
    if not path.lower().endswith(".nif") or ":" in path or any(p in ("",".","..") for p in path.split("\\")) or "\0" in path:raise ValueError("Expected relative NIF path")
    if path.lower().startswith("meshes\\"):path=path[7:]
    return b"MODL",path.encode("cp1252")+b"\0"
