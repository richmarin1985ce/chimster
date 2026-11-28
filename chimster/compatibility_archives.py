"""Archive header classification only; no extraction or proprietary assets."""
import struct

def inspect(data):
    if len(data)<8:raise ValueError("Truncated archive header")
    magic,version=struct.unpack_from("<4sI",data)
    if magic==b"BSA\0":
        if len(data)<36:raise ValueError("Truncated BSA header")
        return {"family":"BSA","version":version,"recognized_version":version in (103,104,105),"extraction_verified":False}
    if magic==b"BTDX":
        if len(data)<24:raise ValueError("Truncated BA2 header")
        kind,count,offset=struct.unpack_from("<4sIQ",data,8)
        return {"family":"BA2","version":version,"kind":kind.decode("ascii"),"files":count,"name_table_offset":offset,"extraction_verified":False}
    if magic==b"\x00\x01\x00\x00":
        if len(data)<12:raise ValueError("Truncated TES3 archive header")
        return {"family":"TES3-BSA","hash_offset":version,"files":struct.unpack_from("<I",data,8)[0],"extraction_verified":False}
    raise ValueError("Unknown archive signature")
