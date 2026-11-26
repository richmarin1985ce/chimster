"""Compare frame-time traces captured externally during matched game runs."""
import csv,math,statistics
from pathlib import Path

def load_trace(path,column="frame_ms"):
    with Path(path).open(newline="",encoding="utf-8-sig") as f:
        rows=csv.DictReader(f)
        if not rows.fieldnames or column not in rows.fieldnames:raise ValueError("missing frame time column")
        data=[float(r[column]) for r in rows]
    return summarize(data)

def summarize(times):
    if not times or any(not math.isfinite(t) or t<=0 for t in times):raise ValueError("invalid frame trace")
    ordered=sorted(times);n=len(times)
    def pct(p):return ordered[max(0,math.ceil(n*p)-1)]
    mean=statistics.fmean(times)
    return {"frames":n,"duration_seconds":sum(times)/1000,"mean_fps":1000/mean,"median_ms":statistics.median(times),"p95_ms":pct(.95),"p99_ms":pct(.99),"worst_ms":ordered[-1],"frames_over_33_3_ms":sum(t>1000/30 for t in times)}

def compare(base,changed):
    a,b=load_trace(base),load_trace(changed)
    return {"baseline":a,"changed":b,"fps_change_pct":100*(b["mean_fps"]/a["mean_fps"]-1),
            "p95_change_pct":100*(b["p95_ms"]/a["p95_ms"]-1),
            "warning":"External traces; ensure same game build, camera route, hardware, settings and capture duration. No causal claim."}
