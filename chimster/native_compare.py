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

def semantic_compare(profile,left,left_path,left_slots,right,right_path,right_slots):
    """Compare known links by persistent identity, not raw load-order slot.

    Opaque fields are never certified equivalent across differing master tables.
    """
    from .native_edit import semantic_fields
    from .native_profiles import PROFILES
    a=at(profile,left,left_path);b=at(profile,right,right_path)
    result=compare(profile,left,left_path,right,right_path)
    if PROFILES[profile].family=="TES3":
        result["semantic_coverage"]="named records; binary comparison only"
        return result
    aa,ao=semantic_fields(profile,a,left_slots);bb,bo=semantic_fields(profile,b,right_slots)
    def keyed(rows,opaque):
        counts=Counter();out={}
        for i,(tag,raw,targets) in enumerate(rows):
            key=(tag.decode("ascii",errors="replace"),counts[tag]);counts[tag]+=1
            out[key]=(raw,targets,i in opaque)
        return out
    x=keyed(aa,ao);y=keyed(bb,bo)
    for row in result["fields"]:
        key=(row["tag"],row["occurrence"])
        p=x.get(key);q=y.get(key)
        if p is None or q is None:
            row["semantic_status"]=row["status"];continue
        if p[2] or q[2]:
            row["semantic_status"]="opaque-"+row["status"]
        else:
            row["semantic_status"]="equivalent" if p[:2]==q[:2] else "conflict"
        row["left_targets"]=[(offset,{"origin":target.origin,"local_id":target.local}) for offset,target in p[1]]
        row["right_targets"]=[(offset,{"origin":target.origin,"local_id":target.local}) for offset,target in q[1]]
    result["semantic_coverage"]="partial" if ao or bo else "known fields"
    result["master_tables_equal"]=left_slots.names==right_slots.names
    return result
