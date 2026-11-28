"""Conservative initial catalogs. Unlisted layouts remain opaque."""
from dataclasses import dataclass
import struct
from .native_profiles import PROFILES, Tes3Key

@dataclass(frozen=True)
class Field:
    length: int
    offset: int
    targets: tuple = ()

# Explicitly enumerated game families, not automatic inheritance.
def fields(*entries):
    return {(sig, tag): Field(size, offset, targets) for sig,tag,size,offset,targets in entries}

PLACED = ("REFR", b"NAME", 4, 0, ())
SPELL = ("SPEL", b"EFID", 4, 0, ("MGEF",))
LIST = ("FLST", b"LNAM", 4, 0, ())
RACE = ("NPC_", b"RNAM", 4, 0, ("RACE",))
VOICE = ("NPC_", b"VTCK", 4, 0, ("VTYP",))
CATALOGS = {
    "morrowind": {},
    "oblivion": fields(PLACED, RACE),
    "oblivion-remastered": {}, # independently validate
    "skyrim-vr": {}, # structural inspection only, no inherited field offsets
    "fallout4-vr": {},
    "fallout3": fields(PLACED, LIST, RACE, VOICE, SPELL),
    "new-vegas": fields(PLACED, LIST, RACE, VOICE, SPELL),
    "skyrim": fields(PLACED, LIST, RACE, VOICE, SPELL),
    "skyrim-se": fields(PLACED, LIST, RACE, VOICE, SPELL),
    "fallout4": fields(PLACED, LIST, RACE, VOICE, SPELL),
}
# Fixed-width reference fields only. Variable layouts require separate codecs.
def extend(profile, *entries):
    CATALOGS[profile].update(fields(*entries))

for profile in ("oblivion", "fallout3", "new-vegas", "skyrim", "skyrim-se", "fallout4"):
    extend(profile,
        ("ACHR", b"NAME", 4, 0, ("NPC_",)),
        ("REFR", b"XOWN", 4, 0, ("NPC_", "FACT")),
        ("CELL", b"XOWN", 4, 0, ("NPC_", "FACT")),
        ("NPC_", b"CNAM", 4, 0, ("CLAS",)))
for profile in ("oblivion", "fallout3", "new-vegas"):
    extend(profile,
        ("ACRE", b"NAME", 4, 0, ("CREA",)),
        ("NPC_", b"PKID", 4, 0, ("PACK",)),
        ("CREA", b"PKID", 4, 0, ("PACK",)),
        ("NPC_", b"CNTO", 8, 0, ()),
        ("CREA", b"CNTO", 8, 0, ()),
        ("CONT", b"CNTO", 8, 0, ()))
for profile in ("skyrim", "skyrim-se", "fallout4"):
    extend(profile,
        ("NPC_", b"PKID", 4, 0, ("PACK",)),
        ("NPC_", b"CNTO", 8, 0, ()),
        ("CONT", b"CNTO", 8, 0, ()),
        ("REFR", b"XEZN", 4, 0, ("ECZN",)),
        ("CELL", b"XEZN", 4, 0, ("ECZN",)))
# Candidate fixed-width layouts; independently validate per game.
for profile in ("fallout3","new-vegas","skyrim","skyrim-se","fallout4"):
    extend(profile,
        ("NPC_",b"SNAM",8,0,("FACT",)),
        ("LVLI",b"LVLG",4,0,("GLOB",)),
        ("ALCH",b"EFID",4,0,("MGEF",)),
        ("ENCH",b"EFID",4,0,("MGEF",)),
        ("REFR",b"XGLB",4,0,("GLOB",)))
for profile in ("fallout3","new-vegas"):
    extend(profile,
        ("LVLI",b"LVLO",12,4,()),
        ("LVLN",b"LVLO",12,4,("NPC_","LVLN")))
# TES3 NAME is not universally a record identity (e.g. CELL and INFO).
TES3_NAMED = frozenset(("NPC_", "CREA", "WEAP", "ARMO", "CLOT", "BOOK",
                       "ALCH", "INGR", "MISC", "CONT", "ACTI", "STAT",
                       "DOOR", "SPEL", "RACE", "CLAS", "FACT", "REGN",
                       "SOUN", "GMST", "GLOB"))

def named_key(signature, parts, encoding="cp1252"):
    if signature not in TES3_NAMED:
        return None
    names = [raw for tag,raw in parts if tag==b"NAME"]
    if len(names)!=1:
        return None
    raw=names[0].rstrip(b"\0")
    if not raw or b"\0" in raw:
        return None
    return Tes3Key(signature, raw.decode(encoding))

def references(profile, signature, parts, slots, include_null=False):
    parts = list(parts)
    catalog = CATALOGS[profile]
    edges, opaque = [], []
    for i,(tag,raw) in enumerate(parts):
        spec = catalog.get((signature,tag))
        if spec is None or len(raw)!=spec.length:
            opaque.append(i)
            continue
        target = slots.decode(struct.unpack_from("<I",raw,spec.offset)[0])
        if target is not None or include_null:
            edges.append((i,spec.offset,target,spec.targets))
    if profile == "new-vegas":
        from .schema_reference import inspect
        extracted, unknown = inspect(signature, parts, slots, include_null=include_null)
        known = {(i,offset): (i,offset,target,kinds) for i,offset,target,kinds in edges}
        for edge in extracted:
            previous = known.get((edge.field,edge.offset))
            kinds = edge.expected_types or (previous[3] if previous else ())
            known[(edge.field,edge.offset)] = (edge.field,edge.offset,edge.target,kinds)
        edges = list(known.values())
        opaque = sorted(set(opaque) & set(unknown))
    return edges,opaque

def inspect_node(profile, node, slots=None):
    from .native_parser import subrecords
    parts = list(subrecords(profile,node))
    signature = node.signature.decode("ascii")
    if PROFILES[profile].family=="TES3":
        return {"key":named_key(signature,parts), "parts":parts,
                "edges":[], "opaque":list(range(len(parts)))}
    if slots is None:
        raise ValueError("plugin-relative slots required")
    edges,opaque=references(profile,signature,parts,slots)
    return {"key":slots.decode(struct.unpack_from("<I",node.header,12)[0]),
            "parts":parts,"edges":edges,"opaque":opaque}
