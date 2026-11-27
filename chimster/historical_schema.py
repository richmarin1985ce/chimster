"""Versioned group-label semantics; no inference from opaque bytes."""
import struct

# Explicitly supported classic group types. Later formats require verification.
BASE={0:"signature",1:"world",2:"index",3:"index",4:"grid",5:"grid",6:"cell",7:"topic",8:"cell",9:"cell",10:"cell"}
PARENTS={"world":"WRLD","cell":"CELL","topic":"DIAL"}

def group_label(kind, label, slots):
    if kind not in BASE or len(label)!=4:
        raise ValueError("unsupported group label")
    role=BASE[kind]
    if role in PARENTS:
        identity=slots.decode(struct.unpack("<I",label)[0])
        if identity is None:raise ValueError("null group owner")
        return role,identity
    return role,label

def remap_group_label(kind,label,source,destination):
    role,value=group_label(kind,label,source)
    return struct.pack("<I",destination.encode(value)) if role in PARENTS else label

def check_group_owner(kind,label,slots,records):
    role,value=group_label(kind,label,slots)
    if role in PARENTS and records.get(value)!=PARENTS[role]:
        raise ValueError("missing or mismatched group owner")
    return value

class SchemaRegistry:
    """Explicit parent revisions and field deltas; unknown fields remain unknown."""
    def __init__(self):
        self.revisions={}
    def register(self,name,parent=None,changes=None):
        if name in self.revisions or (parent is not None and parent not in self.revisions):
            raise ValueError("duplicate revision or missing parent")
        fields=dict(self.revisions[parent]) if parent is not None else {}
        for key,value in (changes or {}).items():
            if value is None:fields.pop(key,None)
            else:fields[key]=value
        self.revisions[name]=fields
    def fields(self,name):
        return dict(self.revisions[name])
