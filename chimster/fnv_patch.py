"""Narrow native FNV GMST override patch writer. No source plugin deactivation."""
from pathlib import Path
import struct,math
from .fnv_records import scan,subs,text,HEADER,MAX_RECORD
from .loadorder import dependency_order,plugin_name,fingerprint

def sub(k,v):
    if len(v)>65535:raise ValueError("oversized subrecord")
    return struct.pack("<4sH",k,len(v))+v
def record(k,body,form=0,version=15):
    return HEADER.pack(k,len(body),0,form,0,version,0)+body

def build_gmst_patch(paths,output,origin,local_ids):
    paths=[Path(p).resolve(strict=True) for p in paths]
    out=Path(output)
    if out.suffix.lower()!=".esp" or out.exists() or out.is_symlink():raise ValueError("expected new ESP")
    if plugin_name(out.name) in {plugin_name(p.name) for p in paths}:raise ValueError("output name collides with input")
    if not local_ids or len(set(local_ids))!=len(local_ids) or any(not isinstance(i,int) or not 0x800<=i<=0xffffff for i in local_ids):raise ValueError("invalid IDs; reserved forms excluded")
    names=[plugin_name(p.name) for p in paths];origin=plugin_name(origin)
    if origin not in names:raise ValueError("origin missing")
    hashes=[fingerprint(p) for p in paths];reports=[scan(p) for p in paths]
    if [plugin_name(n) for n in dependency_order(reports)]!=names:raise ValueError("invalid order")
    base=paths[names.index(origin)]
    if reports[names.index(origin)]["masters"]:raise ValueError("initial writer requires self-contained origin master")
    if base.suffix.lower()!=".esm":raise ValueError("origin must be ESM")
    with base.open("rb") as f:
        if HEADER.unpack(f.read(24))[2]!=1:raise ValueError("origin is not a master")
    payloads=[];provenance=[]
    for local in sorted(local_ids):
        chain=[(p,r) for p,report in zip(paths,reports) for r in report["records"] if r["origin"]==origin and r["local_id"]==local]
        if not chain or plugin_name(chain[0][0].name)!=origin or any(r["signature"]!="GMST" or r["flags"] for p,r in chain):raise ValueError("not an ordinary existing GMST chain")
        edids={r["editor_id"] for _,r in chain}
        if len(edids)!=1 or None in edids:raise ValueError("inconsistent EditorID")
        provider,r=chain[-1]
        with provider.open("rb") as f:
            f.seek(r["offset"]);sig,n,flags,form,vc,ver,unk=HEADER.unpack(f.read(24))
            if sig!=b"GMST" or n>MAX_RECORD or flags or form&0xffffff!=local:raise ValueError("record changed")
            body=f.read(n)
        import hashlib
        if len(body)!=n or hashlib.sha256(body).hexdigest()!=r["payload_sha256"]:raise ValueError("payload changed")
        parts=list(subs(body))
        if [k for k,_ in parts]!=[b"EDID",b"DATA"]:raise ValueError("unsupported GMST layout")
        edid=text(parts[0][1]);value=parts[1][1]
        if edid.startswith("s"):text(value)
        elif edid.startswith("i") and len(value)==4:pass
        elif edid.startswith("f") and len(value)==4 and math.isfinite(struct.unpack("<f",value)[0]):pass
        else:raise ValueError("unsupported GMST value type")
        payloads.append(record(b"GMST",body,local,ver))
        provenance.append({"origin":base.name,"local_id":local,"editor_id":edid,"source":provider.name,"payload_sha256":r["payload_sha256"]})
    if hashes!=[fingerprint(p) for p in paths]:raise ValueError("inputs changed")
    body=b"".join(payloads)
    hedr=sub(b"HEDR",struct.pack("<fII",1.34,len(payloads)+1,0x800))+sub(b"CNAM",b"Chimster\0")+sub(b"MAST",base.name.encode("cp1252")+b"\0")+sub(b"DATA",struct.pack("<Q",base.stat().st_size))
    raw=record(b"TES4",hedr)+struct.pack("<4sI4sIII",b"GRUP",24+len(body),b"GMST",0,0,0)+body
    with out.open("xb") as f:f.write(raw)
    try:
        check=scan(out)
        expected={(r["local_id"],r["payload_sha256"]) for r in provenance}
        if check["masters"]!=[base.name] or {(r["local_id"],r["payload_sha256"]) for r in check["records"]}!=expected:raise ValueError("patch roundtrip failed")
    except Exception:
        out.unlink();raise
    return {"output":str(out),"records":provenance,"source_plugins_disabled":False,"status":"native FNV ESP; self-reader verified only; validate in xEdit/game before use"}
