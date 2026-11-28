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
