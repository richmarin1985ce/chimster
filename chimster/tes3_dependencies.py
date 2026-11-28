"""Classic TES3 master and cell inspection, without modifying plugins."""
import struct
from .native_parser import parse,subrecords

def text(raw):
    return raw.split(b"\0",1)[0].decode("cp1252")

def masters(data):
    nodes=parse("morrowind",data)
    if not nodes or nodes[0].signature!=b"TES3":raise ValueError("Missing TES3 header")
    parts=list(subrecords("morrowind",nodes[0]))
    result=[]
    for i,(tag,raw) in enumerate(parts):
        if tag!=b"MAST":continue
        name=text(raw)
        if not name or i+1>=len(parts) or parts[i+1][0]!=b"DATA" or len(parts[i+1][1])!=8:raise ValueError("Malformed master declaration")
        if name.casefold() in {r["name"].casefold() for r in result}:raise ValueError("Duplicate master")
        result.append({"name":name,"size":struct.unpack("<Q",parts[i+1][1])[0]})
    return result

def validate_order(plugins):
    seen={};issues=[]
    for name,data in plugins:
        key=name.casefold()
        if key in seen:raise ValueError("Duplicate plugin")
        for master in masters(data):
            m=master["name"].casefold()
            if m not in seen:issues.append({"plugin":name,"master":master["name"],"issue":"missing_or_late"})
            elif len(seen[m])!=master["size"]:issues.append({"plugin":name,"master":master["name"],"issue":"size_mismatch"})
        seen[key]=data
    return issues

def cells(plugins):
    rows={}
    for plugin,data in plugins:
        for node in parse("morrowind",data):
            if node.signature!=b"CELL":continue
            parts=list(subrecords("morrowind",node))
            name=next((text(v) for k,v in parts if k==b"NAME"),"")
            raw=next((v for k,v in parts if k==b"DATA"),None)
            if raw is None or len(raw)!=12:continue
            flags,x,y=struct.unpack("<Iii",raw)
            interior=bool(flags&1)
            key=("interior",name.casefold()) if interior else ("exterior",x,y)
            if any(k==b"DELE" for k,v in parts[:3]):rows.pop(key,None);continue
            rows[key]={"name":name,"interior":interior,"grid":None if interior else (x,y),"plugin":plugin}
    return list(rows.values())

def search_cells(rows,query="",limit=100):
    if type(limit)!=int or not 1<=limit<=10000:raise ValueError("Invalid limit")
    q=query.casefold().strip()
    return [dict(r) for r in rows if q in r["name"].casefold() or (r["grid"] is not None and q in ("%s,%s"%r["grid"]))][:limit]
