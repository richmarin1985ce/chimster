"""Experimental native FNV world draft export; preserve source records and slot mappings."""
from pathlib import Path
from collections import defaultdict
import struct
from math import degrees, floor, isclose
from .native_parser import parse, subrecords
from .record_graph import Slots
from .loadorder import plugin_name, fingerprint
from .fnv_patch import record, sub
from .fnv_world import group, cstr
from .fnv_content import reference
from .world_browser import Browser


def export_esp(draft, output):
    original=draft.original
    paths=getattr(original,"source_paths",None)
    hashes=getattr(original,"source_hashes",None)
    out=Path(output)
    if not paths or not hashes or not draft.rows:
        raise ValueError("Load source plugins and stage edits first")
    if out.name.casefold()!=draft.name or out.exists() or out.is_symlink():
        raise ValueError("Choose a new output named "+draft.name)
    if tuple(fingerprint(p) for p in paths)!=hashes:
        raise ValueError("Source plugins changed; rebuild draft")
    names=tuple(plugin_name(p.name) for p in paths)
    slots=Slots(out.name,names)
    index=draft.index()
    source={}
    wanted=set(draft.rows)
    cells={k for k,r in draft.rows.items() if r["signature"]=="CELL"}
    refs=[r for r in draft.rows.values() if r["signature"]=="REFR"]
    cells.update(r["cell"] for r in refs)
    worlds={index.active[k]["world"] for k in cells if index.active[k]["world"] is not None}
    wanted.update(cells|worlds)
    for p in paths:
        nodes=parse("new-vegas",p.read_bytes())
        masters=[v.rstrip(b"\0").decode("cp1252") for t,v in subrecords("new-vegas",nodes[0]) if t==b"MAST"]
        local=Slots(p.name,masters)
        def walk(items):
            for node in items:
                if node.signature==b"GRUP":walk(node.children)
                elif node.signature in (b"WRLD",b"CELL",b"REFR"):
                    key=local.decode(struct.unpack_from("<I",node.header,12)[0])
                    if key in wanted:source[key]=(node,local)
        walk(nodes)

    def preserved(key, rename=None):
        if key not in source:raise ValueError("Missing original native owner")
        node,local=source[key]
        # Opaque fields may contain FormIDs: copy only with identical disk slots.
        if slots.names[:len(local.names)]!=local.names:
            raise ValueError("Cannot preserve opaque record with changed master slots: "+str(key))
        flags=struct.unpack_from("<I",node.header,8)[0]
        if flags&0x20:raise ValueError("Deleted source record")
        if rename is None:
            return node.header+node.payload
        if flags&0x40000:raise ValueError("Compressed CELL rename not enabled")
        parts=list(subrecords("new-vegas",node))
        if len([v for t,v in parts if t==b"EDID"])>1:
            raise ValueError("Duplicate editor ID field")
        if any(t==b"EDID" for t,v in parts):
            parts=[(t,cstr(rename) if t==b"EDID" else v) for t,v in parts]
        else:parts.insert(0,(b"EDID",cstr(rename)))
        body=b"".join(sub(t,v) for t,v in parts)
        return node.header[:4]+struct.pack("<I",len(body))+node.header[8:]+body

    records=0
    groups=0
    def g(kind,key,body):
        nonlocal groups
        groups+=1
        return group(kind,key,body)
    def cell_bytes(key):
        nonlocal records
        row=index.active[key]
        if row.get("persistent_cell"):raise ValueError("Persistent owner cell editing is not enabled")
        fid=slots.encode(key)
        records+=1
        if key.origin==draft.name:
            payload=sub(b"EDID",cstr(row["editor_id"]))+sub(b"DATA",b"\1" if row["world"] is None else b"\0")
            if "grid" in row:payload+=sub(b"XCLC",struct.pack("<iiI",*row["grid"],0))
            raw=record(b"CELL",payload,fid)
        else:
            raw=preserved(key,row["editor_id"] if key in draft.rows else None)
        placed=[]
        for ref in sorted(refs,key=lambda r:r["key"]):
            if ref["cell"]!=key:continue
            if ref["key"].origin!=draft.name:
                node,local=source[ref["key"]]
                tags=[tag for tag,_ in subrecords("new-vegas",node)]
                if struct.unpack_from("<I",node.header,8)[0] or tags not in ([b"NAME",b"DATA"],[b"NAME",b"XSCL",b"DATA"]):
                    raise ValueError("Unsupported source reference layout")
            pos=ref["position"]
            packed=struct.unpack("<3f",struct.pack("<3f",*pos))
            if "grid" in row and tuple(floor(v/4096) for v in packed[:2])!=row["grid"]:
                raise ValueError("Float rounding moves reference outside cell")
            placed.append(reference(slots.encode(ref["key"]),slots.encode(ref["base"]),*pos,degrees(ref["rotation"][2]),ref["scale"]))
            records+=1
        return raw+(g(6,fid,g(9,fid,b"".join(placed))) if placed else b"")

    interior=defaultdict(lambda:defaultdict(list))
    exterior=defaultdict(lambda:defaultdict(lambda:defaultdict(list)))
    for key in sorted(cells):
        row=index.active[key]
        raw=cell_bytes(key)
        if row["world"] is None:
            if not row.get("interior"):raise ValueError("Unassigned exterior cell")
            interior[key.local%10][key.local//10%10].append(raw)
        else:
            if "grid" not in row:raise ValueError("Exterior grid missing")
            x,y=row["grid"]
            exterior[row["world"]][(y//32,x//32)][(y//8,x//8)].append(raw)
    body=b""
    if interior:
        body+=g(0,b"CELL",b"".join(g(2,b,b"".join(g(3,s,b"".join(rs)) for s,rs in sorted(ss.items()))) for b,ss in sorted(interior.items())))
    if exterior:
        wrlds=[]
        for world,blocks in sorted(exterior.items()):
            nested=b"".join(g(4,struct.pack("<hh",*b),b"".join(g(5,struct.pack("<hh",*s),b"".join(rs)) for s,rs in sorted(ss.items()))) for b,ss in sorted(blocks.items()))
            wrlds.append(preserved(world)+g(1,slots.encode(world),nested))
            records+=1
        body+=g(0,b"WRLD",b"".join(wrlds))
    header=sub(b"HEDR",struct.pack("<fII",1.34,records+groups,draft.cursor))+sub(b"CNAM",b"Chimster\0")
    for path in paths:
        header+=sub(b"MAST",cstr(path.name))+sub(b"DATA",struct.pack("<Q",path.stat().st_size))
    created=False
    try:
        with out.open("xb") as stream:
            created=True
            stream.write(record(b"TES4",header)+body)
        merged=Browser.open([*paths,out])
        for key,row in draft.rows.items():
            actual=merged.active.get(key)
            if actual is None or any(actual.get(f)!=row.get(f) for f in ("signature","world","cell","grid","editor_id","base")):
                raise ValueError("Native world edit roundtrip mismatch")
            if row["signature"]=="REFR":
                if not all(isclose(a,b,rel_tol=1e-6,abs_tol=1e-5) for field in ("position","rotation") for a,b in zip(actual[field],row[field])) or not isclose(actual.get("scale",1),row["scale"],rel_tol=1e-6):
                    raise ValueError("Native transform roundtrip mismatch")
        from .world_validator import validate
        report=validate([*paths,out])
        if not report["valid"]:raise ValueError("Native world hierarchy check failed: "+str(report["issues"][:4]))
        if tuple(fingerprint(p) for p in paths)!=hashes:
            raise ValueError("Source plugins changed during export")
    except Exception:
        if created:out.unlink()
        raise
    return {"output":str(out),"records":records,"groups":groups,"warnings":report["warnings"],
            "scope":"Experimental FNV ESP; source masters untouched; xEdit/GECK verification required"}
