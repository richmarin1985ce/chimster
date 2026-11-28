"""Documented FNV NAVM fields; preserve unverified grid/unknown data."""
import struct,math
from .navmesh import topology
from .fnv_patch import sub

def inspect(parts):
    parts=list(parts);values={};indices={};edges=[]
    supported={b"EDID",b"NVER",b"DATA",b"NVVX",b"NVTR",b"NVCA",b"NVDP",b"NVGD",b"NVEX"}
    for i,(tag,raw) in enumerate(parts):
        if tag not in supported or tag in values:raise ValueError("unsupported NAVM subrecord layout")
        values[tag]=raw;indices[tag]=i
    if not {b"NVER",b"DATA",b"NVVX",b"NVTR"}<=values.keys() or len(values[b"NVER"])!=4 or len(values[b"DATA"])!=24:
        raise ValueError("missing or invalid NAVM header")
    version=struct.unpack("<I",values[b"NVER"])[0]
    cell,nv,nt,ne,na,nd=struct.unpack("<6I",values[b"DATA"])
    if not cell or not 0<nv<=32768 or not 0<nt<=32768 or max(ne,na,nd)>1000000:raise ValueError("invalid NAVM counts")
    for tag,count,size in ((b"NVVX",nv,12),(b"NVTR",nt,16),(b"NVEX",ne,10),(b"NVCA",na,2),(b"NVDP",nd,8)):
        if len(values.get(tag,b""))!=count*size:raise ValueError("NAVM count mismatch: "+tag.decode())
    vertices=list(struct.iter_unpack("<3f",values[b"NVVX"]))
    rows=list(struct.iter_unpack("<6hI",values[b"NVTR"]))
    if any(not all(math.isfinite(v) for v in p) for p in vertices):raise ValueError("nonfinite NAVM vertex")
    triangles=[r[:3] for r in rows]
    if any(any(not 0<=v<nv for v in t) or len(set(t))!=3 for t in triangles):raise ValueError("invalid native triangle vertex")
    issues=[]
    for i,r in enumerate(rows):
        for e,j in enumerate(r[3:6]):
            if r[6]&(1<<e):
                if not 0<=j<ne:issues.append(("external-index",i,e))
                continue
            if j==-1:continue
            if not 0<=j<nt or j==i:issues.append(("neighbor-index",i,e));continue
            edge={r[e],r[(e+1)%3]};other=rows[j]
            matches=[k for k in range(3) if {other[k],other[(k+1)%3]}==edge]
            if len(matches)!=1 or other[6]&(1<<matches[0]) or other[3+matches[0]]!=i:issues.append(("nonreciprocal-edge",i,e))
    edges.append((indices[b"DATA"],0,("CELL",)))
    doors=[]
    for off in range(0,nd*8,8):
        fid,tri,tail=struct.unpack_from("<IH2s",values[b"NVDP"],off)
        if not fid or tri>=nt:issues.append(("invalid-door",off//8,tri))
        else:edges.append((indices[b"NVDP"],off,("REFR",)))
        doors.append({"raw_target":fid,"triangle":tri,"tail_hex":tail.hex()})
    external=[]
    for off in range(0,ne*10,10):
        prefix,fid,tri=struct.unpack_from("<4sIH",values[b"NVEX"],off)
        if fid:edges.append((indices[b"NVEX"],off+4,("NAVM",)))
        external.append({"prefix_hex":prefix.hex(),"raw_target":fid,"triangle":tri})
    grid=values.get(b"NVGD",b"")
    if grid and len(grid)<36:raise ValueError("invalid NAVM grid header")
    return {"version":version,"raw_cell":cell,"vertices":vertices,"triangles":triangles,
            "neighbors":[r[3:6] for r in rows],"flags":[r[6] for r in rows],"doors":doors,
            "external":external,"issues":issues,"grid_bytes":len(grid),
            "opaque_fields":[tag.decode() for tag in (b"NVCA",b"NVGD") if tag in values]},edges

def draft(mesh,cell_form,version):
    """Return documented geometry fields only, NOT a playable NAVM or ESP."""
    if type(cell_form) is not int or not 0<cell_form<=0xffffffff or type(version) is not int or not 0<=version<=0xffffffff:raise ValueError("explicit cell and format version required")
    vertices=mesh["vertices"];triangles=mesh["triangles"]
    if not 0<len(vertices)<=32768 or not 0<len(triangles)<=32768:raise ValueError("native signed-index limit; tile mesh")
    adjacency=topology(vertices,triangles)["neighbors"]
    return [(b"NVER",struct.pack("<I",version)),(b"DATA",struct.pack("<6I",cell_form,len(vertices),len(triangles),0,0,0)),
            (b"NVVX",b"".join(struct.pack("<3f",*p) for p in vertices)),
            (b"NVTR",b"".join(struct.pack("<6hI",*t,*a,0) for t,a in zip(triangles,adjacency)))]

def remap(parts,resolve):
    """Only patch known FormIDs; require caller to resolve opaque-field policy."""
    parts=list(parts);report,edges=inspect(parts)
    if report["issues"]:raise ValueError("invalid NAVM topology")
    if report["opaque_fields"]:raise ValueError("opaque NAVM grid/auxiliary fields require independent verification")
    changed=0
    for i,off,kinds in edges:
        tag,raw=parts[i];old=struct.unpack_from("<I",raw,off)[0]
        new=resolve(old,kinds);changed+=old!=new
        parts[i]=(tag,raw[:off]+struct.pack("<I",new)+raw[off+4:])
    return parts,changed
