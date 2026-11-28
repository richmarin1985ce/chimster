"""Lossless comparison metadata for desktop record inspection."""
from collections import Counter
import hashlib
from .native_parser import parse,subrecords

def at(profile,data,path):
    nodes=parse(profile,data)
    if not path or any(type(i)!=int or i<0 for i in path):raise ValueError("Invalid path")
    for i in path:
        if i>=len(nodes):raise ValueError("Invalid path")
        node=nodes[i];nodes=node.children
    return node

def fields(profile,node):
    counts=Counter();rows={}
    for index,(tag,raw) in enumerate(subrecords(profile,node)):
        key=(tag,counts[tag]);counts[tag]+=1
        rows[key]={"index":index,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"preview":raw[:64].hex(),"raw":raw}
    return rows

def compare(profile,left,left_path,right,right_path):
    a=at(profile,left,left_path);b=at(profile,right,right_path)
    if a.signature!=b.signature:raise ValueError("Different record types")
    aa=fields(profile,a);bb=fields(profile,b)
    out=[]
    for tag,occ in dict.fromkeys([*aa,*bb]):
        x=aa.get((tag,occ));y=bb.get((tag,occ))
        status="added" if x is None else "removed" if y is None else "changed" if x["raw"]!=y["raw"] else "unchanged"
        out.append({"tag":tag.decode("ascii",errors="replace"),"occurrence":occ,"status":status,"moved":x is not None and y is not None and x["index"]!=y["index"],"left":{k:v for k,v in x.items() if k!="raw"} if x else None,"right":{k:v for k,v in y.items() if k!="raw"} if y else None})
    return {"signature":a.signature.decode("ascii",errors="replace"),"header_changed":a.header!=b.header,"fields":out}
