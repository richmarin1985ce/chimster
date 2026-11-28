"""Read-only quest/dialogue inspection. Unknown condition operands stay opaque."""
import struct
from .native_parser import parse, subrecords
from .native_profiles import PROFILES
from .historical_schema import group_label

# Candidate fixed-width links; no inference from variable-size structures.
LINKS = {
    "oblivion": {("DIAL",b"QSTI"): "QUST", ("QUST",b"SCRI"): "SCPT"},
    "fallout3": {("DIAL",b"QSTI"): "QUST", ("QUST",b"SCRI"): "SCPT"},
    "new-vegas": {("DIAL",b"QSTI"): "QUST", ("QUST",b"SCRI"): "SCPT"},
    "skyrim": {("DIAL",b"QNAM"): "QUST", ("INFO",b"PNAM"): "INFO"},
    "skyrim-se": {("DIAL",b"QNAM"): "QUST", ("INFO",b"PNAM"): "INFO"},
    "fallout4": {("DIAL",b"QNAM"): "QUST", ("INFO",b"PNAM"): "INFO"},
}
KINDS = {b"QUST",b"DIAL",b"INFO",b"SCPT",b"DLBR",b"SCEN"}

def inspect(profile, data, slots):
    if PROFILES[profile].family == "TES3":
        raise ValueError("TES3 dialogue requires ordered named-record decoder")
    links = LINKS.get(profile,{})
    def walk(nodes, ancestry):
        for node in nodes:
            if node.signature == b"GRUP":
                kind = struct.unpack_from("<i",node.header,12)[0]
                role,owner = group_label(kind,node.header[8:12],slots)
                yield from walk(node.children,ancestry+((kind,role,owner),))
            elif node.signature in KINDS:
                signature = node.signature.decode("ascii")
                parts = tuple(subrecords(profile,node))
                edges,opaque,conditions = [],[],[]
                for i,(tag,raw) in enumerate(parts):
                    target_kind = links.get((signature,tag))
                    if target_kind and len(raw)==4:
                        target = slots.decode(struct.unpack("<I",raw)[0])
                        if target is not None:
                            edges.append((i,target,target_kind))
                    else:
                        opaque.append(i)
                    if tag in (b"CTDA",b"CTDT"):
                        conditions.append((i,tag,raw))
                offsets=[]
                if profile=="new-vegas" and node.signature in (b"QUST",b"DIAL",b"INFO"):
                    from .quest_remap_schema import fields as exact_fields
                    try:
                        exact=exact_fields(node.signature,parts)
                    except (ValueError,UnicodeError,struct.error):
                        pass
                    else:
                        edges=[];opaque=[]
                        for i,offset,kinds in exact:
                            target=slots.decode(struct.unpack_from("<I",parts[i][1],offset)[0])
                            offsets.append((i,offset,kinds))
                            if target is not None:edges.append((i,target,kinds[0] if len(kinds)==1 else kinds))
                yield {"identity":slots.decode(struct.unpack_from("<I",node.header,12)[0]),
                       "signature":signature,"ancestry":ancestry,"parts":parts,
                       "edges":edges,"opaque":opaque,"conditions":conditions,"typed_offsets":offsets}
    yield from walk(parse(profile,data),())

def validate(rows, external=None):
    """External records must be supplied for cross-master resolution."""
    rows=list(rows)
    index=dict(external or {})
    seen=set()
    for r in rows:
        identity=r["identity"]
        if identity is None or identity in seen:
            yield identity,None,None,"null-or-duplicate-identity"
        else:
            seen.add(identity);index[identity]=r["signature"]
    topics_by_info={r["identity"]:next((o for _,role,o in reversed(r["ancestry"]) if role=="topic"),None) for r in rows if r["signature"]=="INFO"}
    for row in rows:
        for field,target,kind in row["edges"]:
            actual=index.get(target)
            if actual is None:
                yield row["identity"],field,target,"unresolved"
            elif actual not in ((kind,) if isinstance(kind,str) else kind):
                yield row["identity"],field,target,"wrong-type"
        if row["signature"]=="INFO":
            topics=[owner for _,role,owner in row["ancestry"] if role=="topic"]
            if not topics:
                yield row["identity"],None,None,"missing-topic-group"
            elif index.get(topics[-1])!="DIAL":
                yield row["identity"],None,topics[-1],"unresolved-or-wrong-topic"
            else:
                for field,target,kind in row["edges"]:
                    tag=row["parts"][field][0]
                    if tag==b"TPIC" and target!=topics[-1]:
                        yield row["identity"],field,target,"topic-group-mismatch"
                    if tag==b"PNAM" and target in topics_by_info and topics_by_info[target]!=topics[-1]:
                        yield row["identity"],field,target,"previous-info-topic-mismatch"
