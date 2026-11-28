"""Native FNV NAVM finalization candidate with explicit grid convention.

Grid framing and NAVI opaque data require independent GECK verification.
Produces reviewable native subrecords, not a certified playable plugin.
"""
import math,struct,hashlib
from .navmesh import topology,point
from .fnv_navmesh import inspect

def uint(value,bits=32):
    if type(value) is not int or not 0<=value<(1<<bits):raise ValueError("invalid unsigned native integer")
    return value

def grid(vertices,triangles,divisor,*,count_width):
    """Build conservative XY bucket membership from float32-quantized geometry.

    Explicit count width and divisor are supplied by the caller from a local
    reference. AABB intersection includes boundary triangles in both cells.
    """
    if type(divisor) is not int or not 1<=divisor<=64 or count_width not in (2,4):raise ValueError("explicit supported grid convention required")
    vs=[point(v) for v in vertices]
    if not vs or not triangles or len(triangles)>32768:raise ValueError("grid geometry limit")
    lo=[min(v[k] for v in vs) for k in range(3)];hi=[max(v[k] for v in vs) for k in range(3)]
    dx=(hi[0]-lo[0])/divisor;dy=(hi[1]-lo[1])/divisor
    if min(dx,dy)<=0:raise ValueError("degenerate grid bounds")
    buckets=[[] for _ in range(divisor*divisor)]
    work=0
    for i,t in enumerate(triangles):
        p=[vs[j] for j in t]
        a,b=[max(0,min(divisor-1,math.floor((min(v[k] for v in p)-lo[k])/d-1e-8))) for k,d in enumerate((dx,dy))]
        c,d=[max(0,min(divisor-1,math.floor((max(v[k] for v in p)-lo[k])/step+1e-8))) for k,step in enumerate((dx,dy))]
        work+=(c-a+1)*(d-b+1)
        if work>4000000:raise ValueError("grid membership budget")
        for y in range(b,d+1):
            for x in range(a,c+1):buckets[y*divisor+x].append(i)
    prefix="<H" if count_width==2 else "<I"
    data=struct.pack("<I8f",divisor,dx,dy,*lo,*hi)
    data+=b"".join(struct.pack(prefix,len(b))+b"".join(struct.pack("<h",i) for i in b) for b in buckets)
    return data

def read_grid(raw,triangle_count,count_width):
    if len(raw)<36 or count_width not in (2,4):raise ValueError("invalid grid convention")
    div,dx,dy,*bounds=struct.unpack_from("<I8f",raw)
    if not 1<=div<=64 or not all(math.isfinite(v) for v in (dx,dy,*bounds)) or min(dx,dy)<=0 or any(bounds[i]>bounds[i+3] for i in range(3)):raise ValueError("invalid grid header")
    cells=[];pos=36;prefix="<H" if count_width==2 else "<I"
    for _ in range(div*div):
        if pos+count_width>len(raw):raise ValueError("truncated grid count")
        count=struct.unpack_from(prefix,raw,pos)[0];pos+=count_width
        if count>triangle_count or pos+2*count>len(raw):raise ValueError("invalid grid bucket size")
        row=[x[0] for x in struct.iter_unpack("<h",raw[pos:pos+2*count])];pos+=2*count
        if len(set(row))!=len(row) or any(not 0<=i<triangle_count for i in row):raise ValueError("invalid grid triangle")
        cells.append(row)
    if pos!=len(raw):raise ValueError("trailing grid bytes")
    if len({i for row in cells for i in row})!=triangle_count:raise ValueError("grid omits triangles")
    return {"divisor":div,"cell_size":[dx,dy],"bounds":bounds,"cells":cells}

def finalize(mesh,cell,version,*,divisor,count_width,doors=(),external=(),cover=(),flags=None):
    """Construct a candidate native NAVM payload; explicit unknown bytes required.

    external entries: local triangle/edge, target NAVM/triangle, prefix_hex.
    door entries: reference, triangle, tail_hex. No portable step links inferred.
    """
    uint(cell);uint(version)
    if not cell or version<9:raise ValueError("supported modern FNV version required")
    if mesh.get("links"):raise ValueError("portable off-mesh links must be explicitly resolved before native finalization")
    vs=[struct.unpack("<3f",struct.pack("<3f",*point(v))) for v in mesh["vertices"]]
    ts=[tuple(t) for t in mesh["triangles"]]
    if not 0<len(vs)<=32768 or not 0<len(ts)<=32768:raise ValueError("native signed-index limit")
    adjacency=topology(vs,ts)["neighbors"]
    flags=list(flags) if flags is not None else [0]*len(ts)
    if len(flags)!=len(ts) or any(uint(f)&7 for f in flags):raise ValueError("external edge flags are derived")
    ex=[];used=set()
    for e in external:
        i,j,target,tri=e["triangle"],e["edge"],e["target"],e["target_triangle"]
        uint(i,16);uint(j,16);uint(target);uint(tri,16)
        if i>=len(ts) or j>=3 or not target or tri>32767 or adjacency[i][j]!=-1 or (i,j) in used or len(ex)>=32768:raise ValueError("invalid external boundary edge")
        prefix=bytes.fromhex(e["prefix_hex"])
        if len(prefix)!=4:raise ValueError("explicit external prefix required")
        used.add((i,j));adjacency[i][j]=len(ex);flags[i]|=1<<j
        ex.append(struct.pack("<4sIH",prefix,target,tri))
    dp=[];seen=set()
    for d in doors:
        target,i=d["reference"],d["triangle"];uint(target);uint(i,16)
        if not target or i>=len(ts) or target in seen:raise ValueError("invalid duplicate door binding")
        tail=bytes.fromhex(d["tail_hex"])
        if len(tail)!=2:raise ValueError("explicit door tail required")
        seen.add(target);flags[i]|=0x400;dp.append(struct.pack("<IH2s",target,i,tail))
    if any(bool(f&0x400)!=(i in {d["triangle"] for d in doors}) for i,f in enumerate(flags)):raise ValueError("door flag mismatch")
    cover=list(cover)
    if len(set(cover))!=len(cover) or any(type(i) is not int or not 0<=i<len(ts) for i in cover):raise ValueError("invalid cover triangle")
    spatial=grid(vs,ts,divisor,count_width=count_width)
    read_grid(spatial,len(ts),count_width)
    parts=[(b"NVER",struct.pack("<I",version)),(b"DATA",struct.pack("<6I",cell,len(vs),len(ts),len(ex),len(cover),len(dp))),
           (b"NVVX",b"".join(struct.pack("<3f",*p) for p in vs)),
           (b"NVTR",b"".join(struct.pack("<6hI",*t,*a,f) for t,a,f in zip(ts,adjacency,flags)))]
    if cover:parts.append((b"NVCA",b"".join(struct.pack("<h",i) for i in cover)))
    if dp:parts.append((b"NVDP",b"".join(dp)))
    parts.append((b"NVGD",spatial))
    if ex:parts.append((b"NVEX",b"".join(ex)))
    report,_=inspect(parts)
    if report["issues"]:raise ValueError("native candidate topology failed")
    return {"fields":[[k.decode(),v.hex()] for k,v in parts],"grid_convention":{"count_width":count_width,"divisor":divisor},
            "payload_sha256":hashlib.sha256(b"".join(k+struct.pack("<I",len(v))+v for k,v in parts)).hexdigest(),
            "review_required":["independent NVGD convention and membership","reciprocal external NAVM edges","XNDP door backlink and NAVI registration","GECK/xEdit and engine traversal"],
            "status":"native NAVM candidate; not a finalized playable ESP"}
