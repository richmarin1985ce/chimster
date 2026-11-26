"""Bounded FNV record inspection and same-name staged text edit.
Preserves other records and raw subrecords; never mutates source or remaps FormIDs."""
from pathlib import Path
import struct,hashlib,os
from .fnv_records import HEADER,MAX_RECORD,scan,subs,text
from .fnv_patch import sub

TEXT_FIELDS={"WRLD":{b"FULL"},"CELL":{b"FULL"},"BOOK":{b"FULL",b"DESC"},"NOTE":{b"FULL"},"STAT":{b"MODL"}}
def inspect(path,origin,local):
    from .loadorder import plugin_name
    p=Path(path);matches=[r for r in scan(p)["records"] if r["origin"]==plugin_name(origin) and r["local_id"]==local]
    if len(matches)!=1:raise ValueError("expected exactly one record")
    r=matches[0]
    with p.open("rb") as f:
        f.seek(r["offset"]);sig,n,flags,*_=HEADER.unpack(f.read(24));body=f.read(n)
    if hashlib.sha256(body).hexdigest()!=r["payload_sha256"]:raise ValueError("record changed")
    if flags&0x40000:return {**r,"fields":None,"status":"compressed payload; editing unsupported"}
    from .record_schema import fields
    return {**r,"fields":fields(r["signature"],r["editor_id"],subs(body))}
def edit_text(source,output,origin,local,field,value,expected_hash):
    if not isinstance(value,str):raise ValueError("expected text")
    return edit_typed(source,output,origin,local,field,value,expected_hash,text_only=True)
def edit_typed(source,output,origin,local,field,value,expected_hash,text_only=False):
    from .record_schema import encode
    p=Path(source).resolve(strict=True);out=Path(output)
    if p.name!=out.name or out.exists() or out.is_symlink() or p==out.resolve():raise ValueError("use new staging directory and identical plugin filename")
    if p.stat().st_size>128*1024*1024:raise ValueError("staged editor limit is 128 MiB")
    info=inspect(p,origin,local)
    if info["payload_sha256"]!=expected_hash:raise ValueError("stale record hash")
    k=field.encode("ascii")
    matches=[f for f in info.get("fields") or [] if f["tag"]==field and f["writable"]]
    if len(matches)!=1 or info["flags"]&0x40020 or text_only and matches[0]["type"] not in {"text","model"}:raise ValueError("unsupported field or record flags")
    v=encode(matches[0]["type"],value)
    raw=p.read_bytes();source_hash=hashlib.sha256(raw).hexdigest();target=info["offset"];parents=[]
    def rebuild(start,end,depth=0):
        if depth>64:raise ValueError("group depth")
        result=[];i=start
        while i<end:
            sig,n,*_=HEADER.unpack_from(raw,i)
            stop=i+n if sig==b"GRUP" else i+24+n
            if stop>end or stop<i+24:raise ValueError("invalid boundary")
            h=raw[i:i+24]
            if i==target:
                body=raw[i+24:stop]
                if hashlib.sha256(body).hexdigest()!=expected_hash:raise ValueError("source changed")
                # Preserve exact original encodings of untouched fields, including XXXX.
                pos=0;pieces=[];count=0
                while pos<len(body):
                    a=pos;tag,size=struct.unpack_from("<4sH",body,pos);pos+=6
                    if tag==b"XXXX":
                        if size!=4 or pos+10>len(body):raise ValueError("bad extended subrecord")
                        size=struct.unpack_from("<I",body,pos)[0];pos+=4
                        tag,_=struct.unpack_from("<4sH",body,pos);pos+=6
                    pos+=size
                    if pos>len(body):raise ValueError("bad field length")
                    if tag==k:pieces.append(sub(k,v));count+=1
                    else:pieces.append(body[a:pos])
                if count!=1:raise ValueError("field must occur exactly once")
                b=b"".join(pieces);result.append(h[:4]+struct.pack("<I",len(b))+h[8:]+b)
                parents.append(i)
            elif sig==b"GRUP" and i<target<stop:
                b=rebuild(i+24,stop,depth+1);result.append(h[:4]+struct.pack("<I",24+len(b))+h[8:]+b)
            else:result.append(raw[i:stop])
            i=stop
        if i!=end:raise ValueError("boundary mismatch")
        return b"".join(result)
    result=rebuild(0,len(raw))
    if len(parents)!=1 or hashlib.sha256(p.read_bytes()).hexdigest()!=source_hash:raise ValueError("source changed or missing target")
    original=scan(p)
    with out.open("xb") as f:f.write(result)
    try:
        after=scan(out)
        a={(r["origin"],r["local_id"],r["signature"]):r["payload_sha256"] for r in original["records"]}
        b={(r["origin"],r["local_id"],r["signature"]):r["payload_sha256"] for r in after["records"]}
        key=(info["origin"],info["local_id"],info["signature"])
        if len(a)!=len(original["records"]) or len(b)!=len(after["records"]) or set(a)!=set(b) or any(a[k]!=b[k] for k in a if k!=key) or after["masters"]!=original["masters"]:raise ValueError("unexpected record changes")
        new=inspect(out,origin,local)
        if not any(f["tag"]==field and f["writable"] for f in new["fields"]):raise ValueError("edited field failed schema check")
        return {"output":str(out),"old_hash":expected_hash,"new_hash":new["payload_sha256"],"untouched_records":len(a)-1,"status":"staged same-name copy; verify in xEdit/game"}
    except Exception:
        out.unlink();raise
