"""Read-only structural parser; preserves unknown payloads."""
from dataclasses import dataclass
import struct
import zlib
from .native_profiles import PROFILES

@dataclass(frozen=True)
class Node:
    signature: bytes
    header: bytes
    payload: bytes
    children: tuple = ()

def parse(profile, data, max_depth=64):
    p = PROFILES[profile]
    def walk(start, end, depth):
        if depth > max_depth:
            raise ValueError("group nesting limit")
        out = []
        while start < end:
            if end-start < p.record_header:
                raise ValueError("truncated header")
            sig, size = struct.unpack_from("<4sI", data, start)
            group = sig == b"GRUP" and p.group_header is not None
            h = p.group_header if group else p.record_header
            stop = start+size if group else start+h+size
            if stop < start+h or stop > end:
                raise ValueError("invalid record extent")
            header = bytes(data[start:start+h])
            payload = bytes(data[start+h:stop])
            children = walk(start+h, stop, depth+1) if group else ()
            out.append(Node(sig, header, payload, children))
            start = stop
        return tuple(out)
    return walk(0, len(data), 0)

def subrecords(profile, node, limit=64*1024*1024):
    p = PROFILES[profile]
    if node.signature == b"GRUP":
        raise ValueError("group is not a record")
    data = node.payload
    tes3 = p.family == "TES3"
    if not tes3 and struct.unpack_from("<I", node.header, 8)[0] & 0x40000:
        if len(data)<4:
            raise ValueError("truncated compressed record")
        expected = struct.unpack_from("<I", data)[0]
        if expected > limit:
            raise ValueError("decompression limit")
        dec = zlib.decompressobj()
        data = dec.decompress(data[4:], expected+1)
        if len(data)!=expected or not dec.eof or dec.unused_data or dec.unconsumed_tail:
            raise ValueError("invalid compressed record")
    if len(data)>limit:
        raise ValueError("payload limit")
    pos=0
    extended=None
    h=8 if tes3 else 6
    while pos<len(data):
        if len(data)-pos<h:
            raise ValueError("truncated subrecord")
        tag,size=struct.unpack_from("<4sI" if tes3 else "<4sH",data,pos)
        pos+=h
        if not tes3 and tag==b"XXXX":
            if extended is not None or size!=4 or pos+4>len(data):
                raise ValueError("invalid extended size")
            extended=struct.unpack_from("<I",data,pos)[0]
            pos+=4
            continue
        if extended is not None:
            size,extended=extended,None
        if pos+size>len(data):
            raise ValueError("truncated subrecord payload")
        yield tag,data[pos:pos+size]
        pos+=size
    if extended is not None:
        raise ValueError("dangling extended size")
