"""Structural writer for native_parser nodes; not a semantic plugin editor."""
from dataclasses import replace
import struct
from .native_profiles import PROFILES
from .native_parser import parse

def serialize(profile, nodes):
    p=PROFILES[profile]
    def emit(node):
        group=node.signature==b"GRUP" and p.group_header is not None
        h=p.group_header if group else p.record_header
        if len(node.header)!=h or node.header[:4]!=node.signature:
            raise ValueError("invalid node header")
        if not group and node.children:
            raise ValueError("record cannot contain child nodes")
        payload=b"".join(map(emit,node.children)) if group else node.payload
        size=len(payload)+(h if group else 0)
        if size>0xffffffff:
            raise ValueError("record exceeds native size")
        header=bytearray(node.header)
        struct.pack_into("<I",header,4,size)
        return bytes(header)+payload
    return b"".join(map(emit,nodes))

def replace_payload(profile, data, path, expected, replacement):
    """Immutable optimistic replacement by structural path, not FormID.

    Caller must validate semantic references, compression and header counts.
    No records are added or removed; unknown sibling bytes are preserved.
    """
    if not path or any(type(i) is not int or i<0 for i in path):
        raise ValueError("invalid node path")
    p=PROFILES[profile]
    def edit(nodes, depth):
        i=path[depth]
        if i>=len(nodes):
            raise ValueError("node path missing")
        node=nodes[i]
        group=node.signature==b"GRUP" and p.group_header is not None
        if depth+1==len(path):
            if group or node.payload!=expected:
                raise ValueError("group or stale payload")
            if node.signature in (b"TES3",b"TES4"):
                raise ValueError("plugin header replacement unsupported")
            node=replace(node,payload=bytes(replacement))
        else:
            if not group:
                raise ValueError("path descends into record")
            node=replace(node,children=edit(node.children,depth+1))
        return nodes[:i]+(node,)+nodes[i+1:]
    result=serialize(profile,edit(parse(profile,data),0))
    parse(profile,result)
    return result
