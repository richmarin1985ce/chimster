"""Read-only structural audit, not game identification or retail certification."""
from .native_profiles import PROFILES
from .native_parser import parse,subrecords
import struct

def audit(profile,data):
    p=PROFILES[profile]
    nodes=parse(profile,data)
    expected=b"TES3" if p.family=="TES3" else b"TES4"
    if not nodes or nodes[0].signature!=expected:raise ValueError("Unexpected plugin header")
    header=list(subrecords(profile,nodes[0]))
    hedr=[v for k,v in header if k==b"HEDR"]
    if len(hedr)!=1 or len(hedr[0])!=(300 if expected==b"TES3" else 12):raise ValueError("Invalid HEDR")
    masters=[]
    for i,(tag,raw) in enumerate(header):
        if tag!=b"MAST":continue
        if not raw.endswith(b"\0") or not raw[:-1] or b"\0" in raw[:-1]:raise ValueError("Invalid master name")
        if i+1>=len(header) or header[i+1][0]!=b"DATA" or len(header[i+1][1])!=8:raise ValueError("Invalid master metadata")
        masters.append(raw[:-1].decode("cp1252"))
    if len(set(n.casefold() for n in masters))!=len(masters):raise ValueError("Duplicate master")
    counts={};groups=0;compressed=0
    stack=list(reversed(nodes[1:]))
    while stack:
        node=stack.pop()
        if node.signature==b"GRUP":
            groups+=1;stack.extend(reversed(node.children));continue
        if node.signature in (b"TES3",b"TES4"):raise ValueError("Unexpected nested plugin header")
        for _ in subrecords(profile,node):pass
        key=node.signature.decode("ascii")
        counts[key]=counts.get(key,0)+1
        if expected==b"TES4" and struct.unpack_from("<I",node.header,8)[0]&0x40000:compressed+=1
    return {"profile":profile,"masters":masters,"record_types":counts,"groups":groups,"compressed_records":compressed,"structural_valid":True,"experimental":p.experimental,"game_identity_verified":False,"retail_verified":False}
