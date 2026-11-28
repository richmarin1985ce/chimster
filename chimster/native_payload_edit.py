"""Structural payload replacement; does not validate game-specific semantics."""
import hashlib
import struct
import zlib
from .native_parser import parse, subrecords
from .native_profiles import PROFILES

def replace(profile,data,path,tag,occurrence,expected,replacement,revision,*,operation="replace",insert_tag=None):
    if operation not in ("replace","remove","before","after"):raise ValueError("Invalid operation")
    if insert_tag is not None and (operation not in ("before","after") or not isinstance(insert_tag,bytes) or len(insert_tag)!=4 or insert_tag==b"XXXX"):raise ValueError("Invalid insertion tag")
    if hashlib.sha256(data).hexdigest()!=revision:raise ValueError("Stale plugin revision")
    if not path or any(type(i)!=int or i<0 for i in path):raise ValueError("Invalid record path")
    if type(occurrence)!=int or occurrence<0 or len(tag)!=4 or tag==b"XXXX":raise ValueError("Invalid subrecord selector")
    if not isinstance(replacement,bytes) or len(replacement)>64*1024*1024:raise ValueError("Invalid replacement")
    tes3=PROFILES[profile].family=="TES3"
    def patch(nodes,depth):
        index=path[depth]
        if index>=len(nodes):raise ValueError("Record path not found")
        out=[]
        for i,node in enumerate(nodes):
            if i!=index:
                out.append(node.header+node.payload);continue
            header=bytearray(node.header)
            if depth+1<len(path):
                if node.signature!=b"GRUP":raise ValueError("Path traverses record")
                payload=patch(node.children,depth+1)
                struct.pack_into("<I",header,4,len(header)+len(payload))
            else:
                if node.signature==b"GRUP":raise ValueError("Cannot edit group")
                list(subrecords(profile,node))
                compressed=not tes3 and bool(struct.unpack_from("<I",header,8)[0]&0x40000)
                raw=zlib.decompress(node.payload[4:]) if compressed else node.payload
                pos=0;seen=0;extended=None;start=0
                while pos<len(raw):
                    if extended is None:start=pos
                    key,size=struct.unpack_from("<4sI" if tes3 else "<4sH",raw,pos)
                    pos+=8 if tes3 else 6
                    if not tes3 and key==b"XXXX":
                        extended=struct.unpack_from("<I",raw,pos)[0];pos+=4;continue
                    if extended is not None:size=extended;extended=None
                    end=pos+size
                    if key==tag:
                        if seen==occurrence:
                            if raw[pos:end]!=expected:raise ValueError("Stale subrecord value")
                            n=len(replacement)
                            output_tag=insert_tag if insert_tag is not None else tag
                            prefix=struct.pack("<4sI",output_tag,n) if tes3 else (struct.pack("<4sH",output_tag,n) if n<=65535 else struct.pack("<4sHI4sH",b"XXXX",4,n,output_tag,0))
                            encoded=prefix+replacement
                            if operation=="remove":encoded=b""
                            elif operation=="before":encoded+=raw[start:end]
                            elif operation=="after":encoded=raw[start:end]+encoded
                            raw=raw[:start]+encoded+raw[end:];break
                        seen+=1
                    pos=end
                else:raise ValueError("Subrecord not found")
                if len(raw)>64*1024*1024:raise ValueError("Payload limit")
                payload=struct.pack("<I",len(raw))+zlib.compress(raw) if compressed else raw
                struct.pack_into("<I",header,4,len(payload))
            out.append(bytes(header)+payload)
        return b"".join(out)
    result=patch(parse(profile,data),0)
    parse(profile,result)
    return result

def remove(profile,data,path,tag,occurrence,expected,revision):
    return replace(profile,data,path,tag,occurrence,expected,b"",revision,operation="remove")

def insert_adjacent(profile,data,path,tag,occurrence,expected,new_tag,value,revision,*,after=True):
    """Insert a field beside an existing anchor, retaining its exact encoding."""
    if not isinstance(new_tag,bytes) or len(new_tag)!=4 or new_tag==b"XXXX":raise ValueError("Invalid new tag")
    return replace(profile,data,path,tag,occurrence,expected,value,revision,operation="after" if after else "before",insert_tag=new_tag)
