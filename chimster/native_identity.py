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
