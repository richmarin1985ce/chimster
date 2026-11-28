"""Audit a separate GECK-finalized copy of an unfinalized Chimster stage.

No native file is changed; the caller controls GECK and the active load order.
"""
import hashlib,struct,zlib
from pathlib import Path
from .fnv_records import scan,subs,HEADER,MAX_RECORD
from .fnv_navmesh import inspect as inspect_navmesh
from .fnv_navi import inspect as inspect_navi
from .loadorder import plugin_name,fingerprint
from .world_validator import validate

def parts(path,row):
    with Path(path).open("rb") as f:
        f.seek(row["offset"])
        sig,n,flags,form,_,_,_=HEADER.unpack(f.read(24))
        if n>MAX_RECORD or sig.decode("ascii")!=row["signature"]:raise ValueError("record mismatch")
        raw=f.read(n)
    if len(raw)!=n or hashlib.sha256(raw).hexdigest()!=row["payload_sha256"]:raise ValueError("source changed")
    if flags&0x40000:
        if len(raw)<4:raise ValueError("truncated compressed payload")
        size=struct.unpack_from("<I",raw)[0]
        if size>MAX_RECORD:raise ValueError("decompression limit")
        d=zlib.decompressobj();data=d.decompress(raw[4:],size+1)
        if len(data)!=size or not d.eof or d.unused_data or d.unconsumed_tail:raise ValueError("invalid compressed payload")
        raw=data
    return list(subs(raw))

def review(stage,finalized,masters=()):
    a=Path(stage).resolve(strict=True);b=Path(finalized).resolve(strict=True)
    if a==b or plugin_name(a.name)!=plugin_name(b.name):raise ValueError("use separate copies with identical plugin name")
    hashes=[fingerprint(p) for p in (a,b)]
    old,new=scan(a),scan(b)
    if old["masters"]!=new["masters"] or [plugin_name(Path(p).name) for p in masters]!=[plugin_name(p) for p in new["masters"]]:
        raise ValueError("master order changed or not supplied")
    def key(r):return (r["origin"],r["local_id"])
    before={key(r):r for r in old["records"]};after={key(r):r for r in new["records"]}
    issues=[];changes=[];meshes=set();registered=set()
    def geometry(report):
        return sorted(tuple(sorted(tuple(report["vertices"][j]) for j in t)) for t in report["triangles"])
    for k,r in before.items():
        n=after.get(k)
        if not n or n["flags"]&0x20 or n["signature"]!=r["signature"]:
            issues.append({"code":"missing-deleted-or-retyped","identity":k});continue
        if r["signature"]=="NAVM":
            meshes.add(k)
            old_mesh,_=inspect_navmesh(parts(a,r));new_mesh,_=inspect_navmesh(parts(b,n))
            if geometry(old_mesh)!=geometry(new_mesh):issues.append({"code":"navigation-geometry-changed","identity":k})
            if new_mesh["issues"]:issues.append({"code":"navigation-topology","identity":k,"details":new_mesh["issues"]})
        if n["payload_sha256"]!=r["payload_sha256"]:
            changes.append({"identity":k,"signature":r["signature"]})
            if r["signature"] not in ("NAVM","REFR","NAVI"):issues.append({"code":"unexpected-record-change","identity":k})
    for k,r in after.items():
        if k not in before and r["signature"]!="NAVI":issues.append({"code":"unexpected-added-record","identity":k,"signature":r["signature"]})
        if r["signature"]=="NAVI" and not r["flags"]&0x20:
            index,_=inspect_navi(parts(b,r))
            names=[plugin_name(m) for m in new["masters"]]+[plugin_name(b.name)]
            for row in index["entries"]:
                raw=row["mesh"];slot=raw>>24;local=raw&0xffffff
                if slot>=len(names) or not local:issues.append({"code":"invalid-navi-identity","raw":raw})
                else:registered.add((names[slot],local))
    for k in sorted(meshes-registered):issues.append({"code":"missing-finalized-registration","identity":k})
    if not meshes:raise ValueError("stage has no NAVM records")
    audit=validate([*masters,b],navmesh=True)
    if not audit["valid"]:issues.append({"code":"native-load-order-validation","errors":audit["errors"]})
    # Native validator warns on opaque fields and on reciprocal navigation links;
    # report generated-record warnings instead of silently promoting the plugin.
    for row in audit["issues"]:
        if row.get("code") in ("navmesh-unregistered","navmesh-door-backlink","nav-door-triangle","navmesh-external-reciprocity","navmesh-layout","navi-layout","navi-location","navi-grid"):
            issues.append({"code":"navigation-review-warning","detail":row})
    if hashes!=[fingerprint(p) for p in (a,b)]:raise ValueError("source changed during review")
    return {"valid_known_fields":not issues,"issues":issues,"changed_records":changes,"staged_meshes":len(meshes),
            "registered_meshes":len(meshes&registered),"stage_sha256":hashes[0],"finalized_sha256":hashes[1],
            "status":"GECK output review; independent game traversal and opaque data validation still required"}
