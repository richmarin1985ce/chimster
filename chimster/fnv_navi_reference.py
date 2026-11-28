"""Read native NAVI calibration fixtures from a self-contained local FNV master."""
import struct
from pathlib import Path

def extract(path,mesh_ids):
    from .fnv_records import scan
    from .fnv_navmesh_stage import parts
    from .fnv_navmesh import inspect
    from .fnv_navi_variants import decode,infer_grid_order
    from .loadorder import fingerprint,plugin_name
    p=Path(path).resolve(strict=True);digest=fingerprint(p)
    ids=list(mesh_ids)
    if not 1<=len(ids)<=64 or len(set(ids))!=len(ids) or any(type(v) is not int or not 0<v<=0xffffff for v in ids):raise ValueError("select 1–64 unique master-local mesh IDs")
    scan_result=scan(p)
    if scan_result["masters"]:raise ValueError("calibration requires a self-contained master; no implicit FormID remapping")
    name=plugin_name(p.name)
    rows={r["local_id"]:r for r in scan_result["records"] if r["origin"]==name}
    if len(rows)!=len(scan_result["records"]):raise ValueError("duplicate or foreign record identities")
    groups={g["offset"]:g for g in scan_result["groups"]}
    navis=[r for r in rows.values() if r["signature"]=="NAVI" and not r["flags"]&0x20]
    if len(navis)!=1:raise ValueError("expected one active NAVI")
    index={}
    for tag,raw in parts(p,navis[0]):
        if tag!=b"NVMI":continue
        if len(raw)<16:raise ValueError("truncated NVMI")
        fid=struct.unpack_from("<I",raw,4)[0]
        if fid in index:raise ValueError("duplicate NVMI")
        index[fid]=raw
    def record(fid,kind):
        r=rows.get(fid)
        if not r or r["signature"]!=kind or r["flags"]&0x20:raise ValueError("missing active "+kind)
        return r
    def owner(row,kind):
        values=[struct.unpack("<I",bytes.fromhex(groups[g]["label"]))[0] for g in row["groups"] if groups[g]["type"]==kind]
        if len(values)!=1:raise ValueError("missing or ambiguous group owner")
        return values[0]
    refs=[];islands=[];details=[]
    for fid in ids:
        mesh=record(fid,"NAVM");native=parts(p,mesh);report,_=inspect(native)
        if report["issues"]:raise ValueError("invalid reference NAVM topology")
        cell_id=report["raw_cell"]
        if owner(mesh,6)!=cell_id or owner(mesh,9)!=cell_id:raise ValueError("NAVM hierarchy differs from DATA owner")
        cell=record(cell_id,"CELL");cp=dict(parts(p,cell))
        if len(cp.get(b"DATA",b""))!=1:raise ValueError("invalid reference CELL flags")
        raw=index.get(fid)
        if raw is None:raise ValueError("missing reference NVMI")
        sample=decode(raw,grid_order="xy")
        if cp[b"DATA"][0]&1:
            if sample["location"]!=cell_id or sample["grid"]!=(0,0):raise ValueError("interior NVMI location mismatch")
            world=None;grid=(0,0)
        else:
            world=owner(cell,1);record(world,"WRLD")
            if owner(mesh,1)!=world or sample["location"]!=world:raise ValueError("exterior NVMI worldspace mismatch")
            if len(cp.get(b"XCLC",b"")) not in (8,12):raise ValueError("unsupported exterior coordinates")
            grid=struct.unpack_from("<ii",cp[b"XCLC"])
            if any(not -32768<=v<=32767 for v in grid):raise ValueError("native exterior grid exceeds int16")
            refs.append({"nvmi_hex":raw.hex(),"grid":list(grid)})
        if sample["variant"]=="island-candidate-layout":
            islands.append({"nvmi_hex":raw.hex(),"navm":{"form_id":fid,"fields":[[k.decode("ascii"),v.hex()] for k,v in native]}})
        details.append({"mesh":fid,"cell":cell_id,"world":world,"grid":list(grid),"variant":sample["variant"]})
    order=None;reason=None
    if refs:
        try:order=infer_grid_order([(bytes.fromhex(r["nvmi_hex"]),r["grid"]) for r in refs])
        except ValueError as exc:reason=str(exc)
    if fingerprint(p)!=digest:raise ValueError("reference master changed")
    return {"source":str(p),"source_sha256":digest,"grid_references":refs,"grid_order":order,"grid_order_warning":reason,
            "island_references":islands,"meshes":details,"scope":"read-only native reference extraction; island byte-equivalence and runtime behavior still require verification"}
