"""Independent FNV CNTO inventory codec using classic master-relative identities."""
import struct
from .record_graph import Identity,Slots
ITEMS={"ALCH","AMMO","ARMO","BOOK","INGR","KEYM","MISC","NOTE","WEAP","LVLI"}
def encode(entries,slots,records):
    result=[]
    for identity,count in entries:
        if not isinstance(identity,Identity):raise ValueError("Expected stable identity")
        if type(count)!=int or not 1<=count<=2147483647:raise ValueError("Invalid count")
        row=records.get(identity)
        if row is None or row.get("flags",0)&0x20:raise ValueError("Missing or deleted inventory item")
        if row.get("signature") not in ITEMS:raise ValueError("Invalid inventory type")
        result.append((b"CNTO",struct.pack("<Ii",slots.encode(identity),count)))
    return result
def decode(parts,slots):
    result=[]
    for tag,raw in parts:
        if tag!=b"CNTO":continue
        if len(raw)!=8:raise ValueError("Invalid CNTO length")
        fid,count=struct.unpack("<Ii",raw)
        identity=slots.decode(fid)
        if identity is None:raise ValueError("Null inventory reference")
        result.append((identity,count))
    return result
