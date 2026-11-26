"""Identity-based comparison of FNV plugin revisions; no merge or FormID rewriting."""
from .fnv_records import scan
def compare(old,new):
    a,b=scan(old),scan(new)
    def table(r):
        t={(v["origin"],v["local_id"]):v for v in r["records"]}
        if len(t)!=len(r["records"]):raise ValueError("duplicate record identity")
        return t
    x,y=table(a),table(b)
    def desc(k):return {"origin":k[0],"local_id":k[1]}
    return {"added":[desc(k) for k in sorted(y.keys()-x.keys())],"removed":[desc(k) for k in sorted(x.keys()-y.keys())],
      "changed":[{**desc(k),"before":x[k]["payload_sha256"],"after":y[k]["payload_sha256"],"signature_before":x[k]["signature"],"signature_after":y[k]["signature"]} for k in sorted(x.keys()&y.keys()) if any(x[k][f]!=y[k][f] for f in ("payload_sha256","flags","signature"))],
      "masters_changed":a["masters"]!=b["masters"],"scope":"payload/flag comparison by FormID identity, not semantic reference remapping"}
