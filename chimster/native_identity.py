"""Read-only native identity audit and guarded continuation planning."""
from .fnv_records import scan
from .loadorder import plugin_name
from .identity_policy import reserve_hierarchy, AllocationPolicy

def audit(path):
    report=scan(path)
    own=plugin_name(report["name"])
    local=[r["local_id"] for r in report["records"] if r["origin"]==own]
    cursor=report["next_object_id"]
    by_id={(r["origin"],r["local_id"]):r for r in report["records"]}
    issues=[]
    if len(set(local))!=len(local):issues.append("duplicate local IDs")
    if cursor is None:issues.append("missing or malformed HEDR")
    elif local and cursor<=max(local):issues.append("cursor overlaps existing IDs")
    for g in report["groups"]:
        if "warning" in g:issues.append("group at %s: %s"%(g["offset"],g["warning"]))
        owner=g.get("owner")
        if owner:
            row=by_id.get((owner["origin"],owner["local_id"]))
            expected={"world":"WRLD","cell":"CELL","topic":"DIAL"}[g["role"]]
            if row and row["signature"]!=expected:issues.append("wrong group owner type at %s"%g["offset"])
            if row is None and owner["origin"]==own:issues.append("missing local group owner at %s"%g["offset"])
    return {"plugin":own,"cursor":cursor,"occupied":sorted(set(local)),"groups":report["groups"],"issues":issues}

def continuation(path,ledger,parents):
    """Reserve new keys after existing native IDs; never write source plugin."""
    report=audit(path)
    if report["plugin"]!=ledger.plugin:raise ValueError("ledger plugin mismatch")
    if report["issues"]:raise ValueError("; ".join(report["issues"]))
    if set(ledger.entries.values()) & set(report["occupied"]):
        raise ValueError("native IDs overlap ledger; explicit identity reconciliation required")
    return reserve_hierarchy(ledger,parents,AllocationPolicy(),report["cursor"],report["occupied"])


def token(profile,key):
    """Serialize logical identity without load-order or tree-position dependence."""
    import json
    from .native_profiles import PROFILES, Tes3Key
    from .record_graph import Identity
    if PROFILES[profile].family=="TES3" and isinstance(key,Tes3Key):
        fields=["named",key.signature,key.editor_id]
    elif PROFILES[profile].family!="TES3" and isinstance(key,Identity):
        fields=["form",key.origin,key.local]
    else:raise ValueError("identity incompatible with profile")
    return json.dumps([1,profile,*fields],ensure_ascii=True,separators=(",",":"))

def parse_token(value,profile=None):
    import json
    from .native_profiles import PROFILES, Tes3Key
    from .record_graph import Identity
    fields=json.loads(value)
    if not isinstance(fields,list) or len(fields)!=5 or type(fields[0]) is not int or fields[0]!=1:
        raise ValueError("unsupported identity token")
    _,game,kind,a,b=fields
    if not isinstance(game,str) or game not in PROFILES or (profile is not None and game!=profile):
        raise ValueError("identity profile mismatch")
    if kind=="named" and PROFILES[game].family=="TES3" and isinstance(a,str) and isinstance(b,str):
        key=Tes3Key(a,b)
    elif kind=="form" and PROFILES[game].family!="TES3":
        key=Identity(a,b)
    else:raise ValueError("identity kind mismatch")
    return game,key


def tes3_placed_references(parts, plugin, masters=()):
    """Extract CELL FRMR identities without confusing them with CELL names.

    TES3 reference numbers use the high byte for the source master
    (one-based), zero for the current plugin. Preserve moved references
    as opaque until MVRF/CNDT reconciliation is implemented.
    """
    import struct
    from .record_graph import Identity
    from .loadorder import plugin_name
    origins=(plugin_name(plugin),)+tuple(plugin_name(m) for m in masters)
    if len(origins)>256 or len(set(origins))!=len(origins):
        raise ValueError("invalid TES3 master table")
    rows=[]
    seen=set()
    issues=[]
    moved=False
    for index,(tag,raw) in enumerate(parts):
        if tag==b"MVRF":
            moved=True
            issues.append(("moved-reference",index))
        if tag!=b"FRMR":
            continue
        if len(raw)!=4:
            issues.append(("malformed-reference",index))
            continue
        number=struct.unpack("<I",raw)[0]
        slot,local=number>>24,number&0xffffff
        if slot>=len(origins) or not local:
            issues.append(("invalid-reference",index))
            continue
        key=Identity(origins[slot],local)
        if key in seen:issues.append(("duplicate-reference",index,key))
        seen.add(key)
        rows.append({"key":key,"field":index,"moved_context":moved})
        moved=False
    return {"references":rows,"issues":issues,"complete":not issues}
