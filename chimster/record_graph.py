"""Shared classic TES4-family identities and typed reference graph.

Full-slot, non-light FNV only for native references. Unknown data is not presumed
reference-free. No arbitrary native deletion or renumbering.
"""
from dataclasses import dataclass
from .loadorder import plugin_name
from collections import defaultdict
import struct

@dataclass(frozen=True, order=True)
class Identity:
    origin: str
    local: int
    def __post_init__(self):
        object.__setattr__(self, "origin", plugin_name(self.origin))
        if type(self.local) is not int or not 0 < self.local <= 0xffffff:
            raise ValueError("invalid local identity")

class Slots:
    def __init__(self, plugin, masters=()):
        self.names=tuple(plugin_name(n) for n in (*masters,plugin))
        if len(self.names)>254 or len(set(self.names))!=len(self.names):
            raise ValueError("invalid slot table")
        self.index={n:i for i,n in enumerate(self.names)}
    def decode(self, raw):
        if type(raw) is not int or not 0<=raw<=0xffffffff:
            raise ValueError("invalid raw FormID")
        if raw==0:return None
        slot=raw>>24
        if slot>=len(self.names):raise ValueError("missing master slot")
        return Identity(self.names[slot],raw&0xffffff)
    def encode(self, identity):
        if identity is None:return 0
        if identity.origin not in self.index:raise ValueError("missing master")
        return self.index[identity.origin]<<24 | identity.local
    def remap(self, raw, destination):
        return destination.encode(self.decode(raw))

# (exact byte length, offset, expected signatures). Deliberately narrow.
FIELDS={
    ("FLST",b"LNAM"):(4,0,None),
    ("CONT",b"CNTO"):(8,0,None),
    ("NPC_",b"CNTO"):(8,0,None),
    ("NPC_",b"SNAM"):(8,0,{"FACT"}),
    ("NPC_",b"PKID"):(4,0,{"PACK"}),
    ("NPC_",b"RNAM"):(4,0,{"RACE"}),
    ("NPC_",b"VTCK"):(4,0,{"VTYP"}),
    ("NPC_",b"CNAM"):(4,0,{"CLAS"}),
    ("FACT",b"XNAM"):(12,0,{"FACT","RACE"}),
    ("FACT",b"WMI1"):(4,0,{"REPU"}),
    ("LVLI",b"LVLO"):(12,4,None),
    ("LVLN",b"LVLO"):(12,4,{"NPC_","LVLN"}),
    ("LVLI",b"LVLG"):(4,0,{"GLOB"}),
    ("AMMO",b"DAT2"):(20,4,{"PROJ"}),
    ("ECZN",b"DATA"):(8,0,{"NPC_","FACT"}),
    ("SPEL",b"EFID"):(4,0,{"MGEF"}),
    ("ALCH",b"EFID"):(4,0,{"MGEF"}),
    ("REFR",b"NAME"):(4,0,None),
}
def references(signature, parts, slots):
    edges=[];opaque=[]
    for i,(tag,raw) in enumerate(parts):
        spec=FIELDS.get((signature,tag))
        if spec is None or len(raw)!=spec[0]:
            opaque.append(i);continue
        _,offset,kinds=spec
        identity=slots.decode(struct.unpack_from("<I",raw,offset)[0])
        if identity is not None:edges.append((i,identity,kinds))
    return edges,opaque

def remap_fields(signature, parts, source, destination):
    """Review-only transform: refuse slot changes when any opaque field exists."""
    edges,opaque=references(signature,parts,source)
    if opaque and source.names!=destination.names:
        raise ValueError("opaque fields prevent safe remap")
    output=list(parts)
    for i,identity,_ in edges:
        tag,raw=output[i];offset=FIELDS[signature,tag][1]
        value=bytearray(raw)
        struct.pack_into("<I",value,offset,destination.encode(identity))
        output[i]=(tag,bytes(value))
    return output

class Graph:
    def __init__(self, records):
        self.records=dict(records);self.incoming=defaultdict(list);self.issues=[];self.opaque=set();self.indexed=set()
    def add(self, owner, signature, parts, slots):
        from .schema_reference import inspect
        parts=list(parts)
        extracted,opaque=inspect(signature,parts,slots)
        # Replacing an override must not retain stale diagnostics or edges.
        for target in list(self.incoming):
            self.incoming[target]=[edge for edge in self.incoming[target] if edge[0]!=owner]
            if not self.incoming[target]:del self.incoming[target]
        self.issues=[issue for issue in self.issues if issue[0]!=owner]
        self.indexed.add(owner)
        self.opaque.discard(owner)
        if opaque:self.opaque.add(owner)
        edges=[]
        for edge in extracted:
            spec=FIELDS.get((signature,parts[edge.field][0]))
            kinds=spec[2] if spec and spec[1]==edge.offset else None
            edges.append((edge.field,edge.target,kinds))
        for i,target,kinds in edges:
            self.incoming[target].append((owner,i))
            row=self.records.get(target)
            if row is None or row.get("flags",0)&0x20:
                self.issues.append((owner,i,target,"missing-or-deleted"))
            elif kinds is not None and row["signature"] not in kinds:
                self.issues.append((owner,i,target,"wrong-type"))
    def deletion_review(self, identity):
        return {"incoming":list(self.incoming.get(identity,())),
                "opaque_records":sorted(self.opaque),
                "safe":identity in self.records and not self.records[identity].get("flags",0)&0x20 and not self.incoming.get(identity) and not self.opaque and not (set(self.records)-self.indexed)}
