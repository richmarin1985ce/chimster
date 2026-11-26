"""Import embedded result scripts compiled by the GECK, without inventing bytecode.

Donor must be a same-name copy of the draft with identical master table, record
identities and all non-script subrecords. Copy only verified embedded collections.
"""
from pathlib import Path
import struct,hashlib
from .fnv_records import scan,subs,HEADER
from .fnv_patch import sub
SCRIPT={b"SCHR",b"SCDA",b"SCTX",b"SLSD",b"SCVR",b"SCRO",b"SCRV"}
def script_parts(parts):
    ordinary=[];scripts=[];i=0
    while i<len(parts):
        k,v=parts[i]
        if k==b"SCHR":
            a=i;i+=1
            while i<len(parts) and parts[i][0] in SCRIPT-{b"SCHR"}:i+=1
            scripts.append(parts[a:i]);ordinary.append((b"SCHR",b""))
        else:
            if k in SCRIPT:raise ValueError("orphan script subrecord")
            ordinary.append((k,v));i+=1
    return ordinary,scripts
def checked(collection,expected_source):
    if [k for k,v in collection[:3]]!=[b"SCHR",b"SCDA",b"SCTX"]:raise ValueError("incomplete compiled script")
    h,bytecode,source=[v for k,v in collection[:3]]
    if len(h)!=20:raise ValueError("invalid SCHR")
    refs,size,variables,typ,flags=struct.unpack_from("<IIIHH",h,4)
    if size!=len(bytecode) or not size or typ!=0:raise ValueError("not a compiled result script")
    if refs!=sum(k in (b"SCRO",b"SCRV") for k,v in collection[3:]) or variables!=sum(k==b"SLSD" for k,v in collection[3:]):raise ValueError("script reference/variable count mismatch")
    def normalized(v):return v.rstrip(b"\0").replace(b"\r\n",b"\n").strip()
    if normalized(source)!=normalized(expected_source):raise ValueError("compiled source does not match draft")
    return collection
def attach(draft,compiled,output):
    p=Path(draft).resolve(strict=True);d=Path(compiled).resolve(strict=True);q=Path(output)
    if p==d or p.name!=d.name or q.name!=p.name or q.exists() or q.is_symlink() or q.resolve() in (p,d):raise ValueError("three distinct same-name plugin paths required")
    if max(p.stat().st_size,d.stat().st_size)>128*1024*1024:raise ValueError("plugin too large")
    a,b=scan(p),scan(d)
    if a["masters"]!=b["masters"]:raise ValueError("master table changed")
    def index(r):
        t={(v["origin"],v["local_id"],v["signature"]):v for v in r["records"]}
        if len(t)!=len(r["records"]):raise ValueError("duplicate identities")
        return t
    x,y=index(a),index(b)
    if set(x)!=set(y):raise ValueError("record identity set changed")
    raw=p.read_bytes();donor=d.read_bytes();changes={};count=0
    for k,r in x.items():
        s=y[k]
        if r["flags"]!=s["flags"]:raise ValueError("record flags changed")
        if r["signature"] not in ("QUST","INFO"):
            if r["payload_sha256"]!=s["payload_sha256"]:raise ValueError("non-script record changed")
            continue
        if r["flags"]&0x40000:raise ValueError("compressed script-bearing record unsupported")
        def get(data,rec):
            _,n,*_=HEADER.unpack_from(data,rec["offset"]);body=data[rec["offset"]+24:rec["offset"]+24+n]
            if hashlib.sha256(body).hexdigest()!=rec["payload_sha256"]:raise ValueError("source changed")
            return list(subs(body))
        old=get(raw,r);new=get(donor,s);o,os=script_parts(old);v,vs=script_parts(new)
        if o!=v or len(os)!=len(vs):raise ValueError("non-script fields or script slots changed")
        merged=[];slots=[]
        for oldslot,newslot in zip(os,vs):
            if [k for k,v in oldslot[:3]]!=[b"SCHR",b"SCDA",b"SCTX"]:raise ValueError("invalid draft script")
            source=oldslot[2][1]
            if source.strip(b"\0\r\n "):
                slots.append(checked(newslot,source));count+=1
            else:
                if oldslot!=newslot:raise ValueError("unexpected script in empty slot")
                slots.append(oldslot)
        if os:
            it=iter(slots)
            for tag,value in o:
                if tag==b"SCHR":merged.extend(next(it))
                else:merged.append((tag,value))
            changes[r["offset"]]=b"".join(sub(k,v) for k,v in merged)
    if not count:raise ValueError("no authored compiled scripts found")
    def walk(start,end,depth=0):
        if depth>64:raise ValueError("group depth")
        result=[];i=start
        while i<end:
            sig,n,*_=HEADER.unpack_from(raw,i);stop=i+n if sig==b"GRUP" else i+24+n
            if not i+24<=stop<=end:raise ValueError("invalid group boundary")
            if sig==b"GRUP":
                body=walk(i+24,stop,depth+1);result.append(raw[i:i+4]+struct.pack("<I",len(body)+24)+raw[i+8:i+24]+body)
            elif i in changes:
                body=changes[i];result.append(raw[i:i+4]+struct.pack("<I",len(body))+raw[i+8:i+24]+body)
            else:result.append(raw[i:stop])
            i=stop
        return b"".join(result)
    result=walk(0,len(raw))
    if p.read_bytes()!=raw or d.read_bytes()!=donor:raise ValueError("source changed")
    with q.open("xb") as f:f.write(result)
    try:
        if set(index(scan(q)))!=set(x):raise ValueError("output identity mismatch")
    except Exception:q.unlink();raise
    return {"output":str(q),"attached_scripts":count,"scope":"structural validation of externally compiled bytecode; engine behavior unverified"}
