"""Review-only consolidation planner over backend-normalized record snapshots.
Never writes an ESP or deactivates plugins. Unknown evidence blocks consolidation."""
from collections import defaultdict
from hashlib import sha256
import json
from .loadorder import plugin_name, dependency_order

def key(row):
    origin=plugin_name(row["origin"])
    local=row["local_id"]
    if not isinstance(local,str) or not local or not all(c in "0123456789abcdefABCDEF" for c in local):
        raise ValueError("invalid normalized local ID")
    return (origin,int(local,16))

def plan(plugins,records,*,backend_version,complete_snapshot=False):
    """Plugin list is in current load order. Each record is backend-normalized
    with origin plugin, local object ID, provider plugin, semantic digest,
    and signature. No inference from raw load-order FormIDs or EDIDs.
    Safety flags are externally attested, not discovered here."""
    order=[plugin_name(p["name"]) for p in plugins]
    if order!=[plugin_name(n) for n in dependency_order(plugins)]:
        raise ValueError("input order violates dependencies")
    byname={plugin_name(p["name"]):p for p in plugins};rank={n:i for i,n in enumerate(order)}
    dependents=defaultdict(set)
    for p in plugins:
        for m in p["masters"]: dependents[plugin_name(m)].add(plugin_name(p["name"]))
    chains=defaultdict(list); byprovider=defaultdict(list); pairs=set()
    for r in records:
        k=key(r); provider=plugin_name(r["provider"])
        digest=r["semantic_sha256"]
        if provider not in rank or k[0] not in rank or rank[k[0]]>rank[provider] or not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("invalid record evidence")
        if (k,provider) in pairs: raise ValueError("duplicate provider/record")
        pairs.add((k,provider));chains[k].append(r);byprovider[provider].append(r)
    for chain in chains.values(): chain.sort(key=lambda r:rank[plugin_name(r["provider"])])
    candidates=[];blocked=[]; conflicts=[]
    for k,chain in sorted(chains.items()):
        if len({r["semantic_sha256"] for r in chain})>1:
            conflicts.append({"origin":k[0],"local_id":format(k[1],"X"),"providers":[r["provider"] for r in chain],"winner":chain[-1]["provider"]})
    for n in order:
        p=byname[n]
        if not p.get("patch_candidate"): continue
        reasons=[]
        if not complete_snapshot: reasons.append("incomplete record snapshot")
        if dependents[n]: reasons.append("required by another plugin")
        if p.get("side_effects_clear") is not True: reasons.append("archive/script/config/save side effects not cleared")
        if p.get("merge_reviewed") is not True: reasons.append("merge semantics not reviewed")
        rows=byprovider[n]
        if not rows: reasons.append("no verified record inventory")
        if any(key(r)[0]==n for r in rows): reasons.append("plugin owns new forms")
        # Restrict initial policy to explicitly simple record types.
        if any(r.get("signature") not in {"GMST","GLOB","KYWD","STAT"} or r.get("safe_override") is not True for r in rows):
            reasons.append("unsupported or unverified override")
        if reasons: blocked.append({"plugin":p["name"],"reasons":reasons})
        else: candidates.append(n)
    removed=set(candidates); forwards=[];redundant=[]
    for k,chain in sorted(chains.items()):
        win=chain[-1]
        if plugin_name(win["provider"]) not in removed: continue
        survivors=[r for r in chain if plugin_name(r["provider"]) not in removed]
        if survivors and survivors[-1]["semantic_sha256"]==win["semantic_sha256"]:
            redundant.append({"origin":k[0],"local_id":format(k[1],"X"),"source":win["provider"]})
        else:
            forwards.append({"origin":k[0],"local_id":format(k[1],"X"),"source":win["provider"],"expected_semantic_sha256":win["semantic_sha256"]})
    fingerprint=sha256(json.dumps({"plugins":plugins,"records":records,"backend":backend_version,"complete":complete_snapshot},sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {"input_fingerprint":fingerprint,"backend_version":backend_version,"conflicts":conflicts,
            "review_candidates":[byname[n]["name"] for n in candidates],"blocked":blocked,"forward_winning_overrides":forwards,"redundant_overrides":redundant,
            "approval_required":True,"writes_plugin":False,"disables_plugins":False,
            "warning":"Proposal only. Backend must copy records with correct master mapping, validate all references and compare post-build winning semantics before any deactivation. Save compatibility and side effects require independent checks."}
