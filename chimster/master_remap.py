"""Conservative master-table changes for a fully known top-level FNV subset."""
from pathlib import Path
import struct,hashlib
from .fnv_records import HEADER,scan,subs,text
from .fnv_patch import sub
from .fnv_bindings import Bindings
from .loadorder import plugin_name
from .remap_schema import PATTERNS,rewrite
from .schema_reference import inspect as inspect_references
from .record_graph import Slots
SCHEMAS={
 b"GMST":(b"EDID",b"DATA"),
 b"GLOB":(b"EDID",b"FNAM",b"FLTV"),
 b"FACT":(b"EDID",b"FULL",b"DATA"),
 b"MISC":(b"EDID",b"OBND",b"FULL",b"MODL",b"DATA"),
 b"STAT":(b"EDID",b"OBND",b"MODL"),
}
def reorder(source,output,masters,*,allow_set_change=False):
    p=Path(source).resolve(strict=True);out=Path(output)
    if p.name!=out.name or out.exists() or out.is_symlink() or p==out.resolve():raise ValueError("new staging directory, same filename required")
    if p.stat().st_size>128*1024*1024:raise ValueError("plugin too large")
    raw=p.read_bytes();report=scan(p);old=[plugin_name(x) for x in report["masters"]]
    b=Bindings(masters,out)
    added=sorted(set(b.names)-set(old));removed=sorted(set(old)-set(b.names))
    if (added or removed) and not allow_set_change:raise ValueError("only a permutation of existing masters is supported without explicit opt-in")
    slots=old+[plugin_name(p.name)];dest=b.names+[plugin_name(p.name)]
    local_ids={(x["origin"],x["local_id"]) for x in report["records"] if not x["flags"]&0x20}
    if len(local_ids)!=len(report["records"]):raise ValueError("duplicate or deleted record identity")
    for row in report["records"]:
        if row["origin"]!=slots[-1]:
            origin=(row["origin"],row["local_id"])
            master=b.records.get(origin)
            if row["origin"] not in b.names or master is None or master["flags"]&0x20 or master["signature"]!=row["signature"]:
                raise ValueError("missing or incompatible override origin: "+str(origin))
    source_slots=Slots(p.name,old)
    local_types={(x["origin"],x["local_id"]):x["signature"] for x in report["records"]}
    def validate_types(signature,parts):
        edges,_=inspect_references(signature,parts,source_slots)
        for edge in edges:
            key=(edge.target.origin,edge.target.local)
            actual=local_types.get(key)
            if actual is None:
                rec=b.records.get(key)
                if rec is not None and not rec["flags"]&0x20:actual=rec["signature"]
            if edge.expected_types and actual not in edge.expected_types:
                raise ValueError("unresolved or wrong-type reference: "+str(key))
    def remap(v):
        if v==0:return 0
        if v>>24>=len(slots) or not v&0xffffff:raise ValueError("invalid FormID")
        origin=slots[v>>24]
        if origin not in dest:raise ValueError("removed master still referenced: "+origin)
        return (dest.index(origin)<<24)|(v&0xffffff)
    def remap_link(v):
        if not v:return 0
        dest_id=remap(v);key=(slots[v>>24],v&0xffffff)
        if v>>24<len(old):
            rec=b.records.get(key)
            if rec is None or rec["flags"]&0x20:raise ValueError("unresolved external reference")
        elif key not in local_ids:raise ValueError("unresolved local reference")
        return dest_id
    sig,n,flags,form,*_=HEADER.unpack_from(raw)
    header=list(subs(raw[24:24+n]));tags=[k for k,_ in header]
    if tags[:2]!=[b"HEDR",b"CNAM"] or tags[2:]!=[k for _ in old for k in (b"MAST",b"DATA")]:raise ValueError("unsupported TES4 header schema")
    if flags or form:raise ValueError("only ordinary ESP supported")
    if len(header[0][1])!=12:raise ValueError("invalid HEDR")
    text(header[1][1])
    if any(len(v)!=8 for k,v in header[2:] if k==b"DATA"):raise ValueError("invalid master DATA")
    body=b"".join(sub(k,v) for k,v in header[:2])+b.header()
    result=[raw[:4]+struct.pack("<I",len(body))+raw[8:24]+body];i=24+n
    links=0
    while i<len(raw):
        g,size,label,typ,_,_=struct.unpack_from("<4sI4sIII",raw,i)
        if g!=b"GRUP" or typ!=0 or size<24 or i+size>len(raw) or label not in set(SCHEMAS)|set(PATTERNS)|{b"FLST"}:raise ValueError("unknown or nested group; remapping refused")
        j=i+24;end=i+size;records=[]
        while j<end:
            if end-j<24:raise ValueError("truncated record")
            k,n,flags,fid,*_=HEADER.unpack_from(raw,j);stop=j+24+n
            if k!=label or stop>end or flags:raise ValueError("unsupported record")
            parts=list(subs(raw[j+24:stop]));tags=tuple(t for t,_ in parts)
            if k==b"FLST":
                if not tags or tags[0]!=b"EDID" or any(t!=b"LNAM" for t in tags[1:]):raise ValueError("unknown list fields")
                new=[]
                for tag,v in parts:
                    if tag==b"LNAM":
                        if len(v)!=4:raise ValueError("invalid LNAM")
                        before=struct.unpack("<I",v)[0];after=remap(before)
                        if not before:raise ValueError("null list reference")
                        if before>>24<len(old):
                            rec=b.records.get((slots[before>>24],before&0xffffff))
                            if rec is None or rec["flags"]&0x20:raise ValueError("unresolved external reference")
                        elif not any(r["origin"]==slots[-1] and r["local_id"]==before&0xffffff and not r["flags"]&0x20 for r in report["records"]):raise ValueError("unresolved local reference")
                        v=struct.pack("<I",after);links+=int(after!=before)
                    new.append(sub(tag,v))
                payload=b"".join(new)
            elif k in PATTERNS:
                validate_types(k.decode("ascii"),parts)
                payload,nchanged=rewrite(k,parts,remap_link);links+=nchanged
            elif tags!=SCHEMAS[k]:raise ValueError("unknown fields; remapping refused")
            else:
                # Fixed known non-reference subrecords only. Validate lengths where defined.
                for tag,v in parts:
                    if tag in (b"EDID",b"FULL",b"MODL"):text(v)
                    elif tag==b"OBND" and len(v)!=12:raise ValueError("invalid bounds")
                    elif k==b"FACT" and tag==b"DATA" and len(v)!=4:raise ValueError("invalid faction flags")
                    elif k==b"MISC" and tag==b"DATA" and len(v)!=8:raise ValueError("invalid item")
                    elif k==b"GLOB" and tag==b"FNAM" and v not in (b"s",b"l",b"f"):raise ValueError("invalid global type")
                    elif k==b"GLOB" and tag==b"FLTV" and len(v)!=4:raise ValueError("invalid global")
                    elif k==b"GMST" and tag==b"DATA":
                        prefix=text(parts[0][1])[:1]
                        if prefix=="s":text(v)
                        elif prefix not in "if" or len(v)!=4:raise ValueError("unknown setting")
                payload=raw[j+24:stop]
            records.append(raw[j:j+4]+struct.pack("<III",len(payload),flags,remap(fid))+raw[j+16:j+24]+payload);j=stop
        records=b"".join(records);result.append(raw[i:i+4]+struct.pack("<I",24+len(records))+raw[i+8:i+24]+records);i=end
    if hashlib.sha256(p.read_bytes()).digest()!=hashlib.sha256(raw).digest():raise ValueError("source changed")
    b.check()
    created=False
    try:
        with out.open("xb") as f:
            created=True
            f.write(b"".join(result))
        after=scan(out)
        def identities(r):return sorted((x["origin"],x["local_id"],x["signature"]) for x in r["records"])
        if identities(report)!=identities(after) or [plugin_name(x) for x in after["masters"]]!=b.names:raise ValueError("remap identity mismatch")
        b.check()
    except Exception:
        if created:out.unlink()
        raise
    return {"output":str(out),"records":len(report["records"]),"changed_list_references":links,"changed_embedded_references":links,"masters":after["masters"],"added_masters":added,"removed_masters":removed,"load_order_review_required":bool(added or removed or old!=b.names),"scope":"known generated top-level subset only; no opaque fields, nested groups or arbitrary local renumbering; dependency changes can alter winning overrides and runtime behavior"}
