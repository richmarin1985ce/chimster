"""Restricted FNV non-island interior NAVI generation and preserved-master extension."""
import math,struct
from collections import defaultdict

def form(v):
    if type(v) is not int or not 0<v<=0xffffffff or not v&0xffffff:raise ValueError("invalid FormID")
    return v

def connection(raw):
    """Decode owner + three uint32-counted FormID arrays."""
    if len(raw)<16:raise ValueError("truncated NVCI")
    owner=form(struct.unpack_from("<I",raw)[0]);pos=4;arrays=[]
    for _ in range(3):
        if pos+4>len(raw):raise ValueError("truncated NVCI count")
        count=struct.unpack_from("<I",raw,pos)[0];pos+=4
        if count>1000000 or pos+4*count>len(raw):raise ValueError("invalid NVCI count")
        values=[form(v[0]) for v in struct.iter_unpack("<I",raw[pos:pos+4*count])]
        arrays.append(values);pos+=4*count
    if pos!=len(raw):raise ValueError("trailing NVCI data")
    return {"mesh":owner,"standard":arrays[0],"preferred":arrays[1],"doors":arrays[2]}

def encode_connection(owner,standard=(),preferred=(),doors=()):
    out=bytearray(struct.pack("<I",form(owner)))
    for values in (standard,preferred,doors):
        seq=sorted(set(form(v) for v in values))
        if len(seq)>1000000:raise ValueError("NVCI array limit")
        out.extend(struct.pack("<I",len(seq)))
        for v in seq:out.extend(struct.pack("<I",v))
    return bytes(out)

def map_entry(owner,cell,vertices):
    """Ordinary 32-byte, non-island interior NVMI; grid zero."""
    if not vertices or len(vertices)>32768:raise ValueError("invalid vertex count")
    if any(len(p)!=3 or not all(math.isfinite(x) and abs(x)<=1e7 for x in p) for p in vertices):raise ValueError("invalid vertex")
    center=[math.fsum(v[k] for v in vertices)/len(vertices) for k in range(3)]
    return struct.pack("<IIIhh4f",0,form(owner),form(cell),0,0,*center,0.)

def extend(master_parts,meshes):
    """Append interior entries to existing runs without changing any master payload.

    meshes are (raw FormID, inspected NAVM report) pairs in the SAME slot space.
    Master must have ordinary ordered NVER/NVMI/NVCI runs; island tails remain
    opaque and untouched. Links to existing master meshes require updating their
    connection data too and are deliberately not supported.
    """
    parts=list(master_parts);head=[];maps=[];connections=[];state=0
    old_maps=set();old_connections=set();version=None
    for tag,raw in parts:
        if tag in (b"EDID",b"NVER") and state==0:
            if tag==b"NVER":
                if version is not None or len(raw)!=4:raise ValueError("invalid NAVI version")
                version=struct.unpack("<I",raw)[0]
            head.append((tag,raw))
        elif tag==b"NVMI" and state<=1:
            state=1
            if len(raw)<16:raise ValueError("truncated master NVMI")
            fid=form(struct.unpack_from("<I",raw,4)[0])
            if fid in old_maps:raise ValueError("duplicate master NVMI")
            old_maps.add(fid);maps.append((tag,raw))
        elif tag==b"NVCI":
            state=2;fid=connection(raw)["mesh"]
            if fid in old_connections:raise ValueError("duplicate master NVCI")
            old_connections.add(fid);connections.append((tag,raw))
        else:raise ValueError("unsupported master NAVI order or field")
    if version is None or not old_maps or old_maps!=old_connections:raise ValueError("incomplete master NAVI map")
    rows={}
    for fid,r in meshes:
        form(fid)
        if fid in old_maps or fid in rows or r["issues"]:raise ValueError("duplicate or invalid new NAVM")
        from .navmesh import topology
        if len(topology(r["vertices"],r["triangles"])["regions"])!=1:raise ValueError("island navigation variants require independent verification")
        if r.get("flags") and any(f&0x40 for f in r["flags"]):raise ValueError("preferred navigation classification is not implemented")
        rows[fid]=r
    if not rows or len(rows)>4096:raise ValueError("new NAVM count limit")
    # Check reciprocal edge ownership and full opposite-winding seam endpoints.
    external=defaultdict(list)
    for fid,r in rows.items():
        for i,ns in enumerate(r["neighbors"]):
            for e,j in enumerate(ns):
                if r["flags"][i]&(1<<e):
                    x=r["external"][j]
                    if x["raw_target"] not in rows or x["raw_target"]==fid:raise ValueError("external mesh must be a distinct new mesh")
                    external[fid,i].append((e,x["raw_target"],x["triangle"]))
    def ends(fid,i,e):
        r=rows[fid];t=r["triangles"][i]
        return r["vertices"][t[e]],r["vertices"][t[(e+1)%3]]
    for (fid,i),edges in external.items():
        for e,target,j in edges:
            back=[k for k,other,tri in external.get((target,j),[]) if other==fid and tri==i]
            if len(back)!=1:raise ValueError("nonreciprocal NAVM edge")
            a,b=ends(fid,i,e);c,d=ends(target,j,back[0])
            if max(math.dist(a,d),math.dist(b,c))>.01:raise ValueError("mismatched NAVM seam")
    new_maps=[];new_connections=[]
    for fid,r in sorted(rows.items()):
        new_maps.append((b"NVMI",map_entry(fid,r["raw_cell"],r["vertices"])))
        new_connections.append((b"NVCI",encode_connection(fid,(e["raw_target"] for e in r["external"]),(),(d["raw_target"] for d in r["doors"]))))
    return head+maps+new_maps+connections+new_connections

def stage_override(stage,master,output):
    """Create a new candidate ESP copy with an extended master NAVI.

    Only a self-contained FalloutNV.esm and new interior-cell records are
    accepted. Never remap opaque master bytes or replace existing master meshes.
    """
    from pathlib import Path
    from .fnv_records import scan,HEADER,MAX_RECORD
    from .fnv_patch import sub,record
    from .fnv_world import group
    from .fnv_navmesh_stage import parts
    from .fnv_navmesh import inspect as inspect_mesh
    from .fnv_portal_fields import inspect as inspect_marker
    from .loadorder import fingerprint,plugin_name
    a=Path(stage).resolve(strict=True);m=Path(master).resolve(strict=True);out=Path(output)
    if out.exists() or out.is_symlink() or plugin_name(out.name)!=plugin_name(a.name) or out.suffix.lower()!=".esp":
        raise ValueError("use new separate output with identical ESP filename")
    if plugin_name(m.name)!="falloutnv.esm" or a.stat().st_size>256*1024*1024:raise ValueError("requires base-game master and bounded stage")
    hashes=[fingerprint(p) for p in (a,m)]
    ar,mr=scan(a),scan(m)
    if mr["masters"] or [plugin_name(x) for x in ar["masters"]]!=["falloutnv.esm"]:raise ValueError("requires exactly the self-contained FalloutNV.esm")
    name=plugin_name(a.name)
    source={r["local_id"]:r for r in ar["records"]}
    if len(source)!=len(ar["records"]) or any(r["origin"]!=name or r["flags"]&0x20 or r["signature"] not in ("CELL","NAVM","REFR","STAT","DOOR") for r in source.values()):
        raise ValueError("requires new interior stage only")
    navis=[r for r in mr["records"] if r["signature"]=="NAVI"]
    if len(navis)!=1 or navis[0]["origin"]!="falloutnv.esm" or navis[0]["flags"]&~0x40000:raise ValueError("unsupported base NAVI")
    navi=navis[0];maps=parts(m,navi)
    def own(fid,kind):
        r=source.get(fid&0xffffff) if fid>>24==1 else None
        if not r or r["signature"]!=kind:raise ValueError("navigation references must be newly authored "+kind)
        return r
    entries=[];bound=set()
    for r in source.values():
        if r["signature"]!="NAVM":continue
        fid=0x1000000|r["local_id"];report,_=inspect_mesh(parts(a,r))
        cell=own(report["raw_cell"],"CELL")
        fields=dict(parts(a,cell))
        if len(fields.get(b"DATA",b""))!=1 or not fields[b"DATA"][0]&1:raise ValueError("only new interior cells supported")
        if len(report["grid_candidates"])!=1:raise ValueError("requires structurally valid native grid")
        for d in report["doors"]:
            ref=d["raw_target"];door=own(ref,"REFR")
            if ref in bound or not door["flags"]&0x400:raise ValueError("duplicate or nonpersistent navigation door")
            bound.add(ref)
            dp=parts(a,door);marker,_=inspect_marker(dp);back=marker.get("navigation_door",{})
            if back.get("raw_target")!=fid or back.get("triangle")!=d["triangle"]:raise ValueError("native door backlink mismatch")
        entries.append((fid,report))
    merged=extend(maps,entries)
    def frame(tag,value):
        if len(value)<=65535:return sub(tag,value)
        return sub(b"XXXX",struct.pack("<I",len(value)))+struct.pack("<4sH",tag,0)+value
    payload=b"".join(frame(tag,value) for tag,value in merged)
    if len(payload)>MAX_RECORD:raise ValueError("NAVI payload limit")
    with m.open("rb") as f:
        f.seek(navi["offset"]);_,_,_,_,_,ver,_=HEADER.unpack(f.read(24))
    navi_group=group(0,b"NAVI",record(b"NAVI",payload,navi["local_id"],ver))
    raw=bytearray(a.read_bytes());sig,size,flags,_,_,_,_=HEADER.unpack_from(raw)
    if sig!=b"TES4" or flags or raw[24:30]!=b"HEDR"+struct.pack("<H",12):raise ValueError("unsupported stage header")
    count=struct.unpack_from("<I",raw,34)[0]
    struct.pack_into("<I",raw,34,count+2)
    offset=24+size;insert=None
    while offset<len(raw):
        if offset+24>len(raw):raise ValueError("truncated group")
        tag,length,label,kind,_,_=struct.unpack_from("<4sI4sIII",raw,offset)
        if tag!=b"GRUP" or kind!=0 or length<24 or offset+length>len(raw):raise ValueError("invalid top-level group")
        if label==b"CELL":
            if insert is not None:raise ValueError("duplicate CELL group")
            insert=offset
        offset+=length
    if insert is None:raise ValueError("missing CELL group")
    if hashes!=[fingerprint(p) for p in (a,m)]:raise ValueError("source changed")
    created=False
    try:
        with out.open("xb") as f:
            created=True;f.write(raw[:insert]);f.write(navi_group);f.write(raw[insert:])
        result=scan(out)
        old={(r["origin"],r["local_id"],r["signature"],r["payload_sha256"]) for r in ar["records"]}
        new={(r["origin"],r["local_id"],r["signature"],r["payload_sha256"]) for r in result["records"]}
        import hashlib
        expected=old|{("falloutnv.esm",navi["local_id"],"NAVI",hashlib.sha256(payload).hexdigest())}
        if new!=expected or len(result["records"])!=len(expected) or result["masters"]!=ar["masters"]:raise ValueError("NAVI stage roundtrip failed")
        if hashes!=[fingerprint(p) for p in (a,m)]:raise ValueError("source changed")
    except Exception:
        if created:out.unlink()
        raise
    return {"output":str(out),"registered_new_meshes":len(entries),"preserved_master_entries":sum(k==b"NVMI" for k,v in maps),"status":"experimental native NAVI override candidate; independent GECK and game validation required"}
