"""GECK result-script source generation. Does not fabricate compiled bytecode."""
from .quest_editor import check_id
from pathlib import Path
import json
def plan(spec):
    q=spec["id"]
    if not check_id(q):raise ValueError("invalid quest ID")
    stages={s["index"] for s in spec["stages"]};objectives={o["index"] for o in spec.get("objectives",[])}
    if any(type(i) is not int or not 0<=i<=255 for i in stages) or any(type(i) is not int or not 0<=i<=2147483647 for i in objectives):raise ValueError("invalid stage or objective")
    def script(actions):
        if not isinstance(actions,list) or len(actions)>64:raise ValueError("invalid actions")
        lines=[]
        for a in actions:
            op=a["op"]
            if op=="stage" and set(a)=={"op","index"} and type(a["index"]) is int and a["index"] in stages:lines.append(f"SetStage {q} {a['index']}")
            elif op in ("display","complete") and set(a)=={"op","index","value"} and type(a["index"]) is int and a["index"] in objectives and type(a["value"]) is bool:
                cmd="SetObjectiveDisplayed" if op=="display" else "SetObjectiveCompleted"
                lines.append(f"{cmd} {q} {a['index']} {int(a['value'])}")
            elif op in ("start","stop") and set(a)=={"op"}:lines.append(("StartQuest" if op=="start" else "StopQuest")+" "+q)
            else:raise ValueError("unsupported action or missing target")
        return "\n".join(lines)+("\n" if lines else "")
    result=[]
    for s in spec["stages"]:
        if s.get("actions"):
            if any(a.get("op")=="stage" and a.get("index")==s["index"] for a in s["actions"]):raise ValueError("self-recursive stage action")
            result.append({"slot":f"stage_{s['index']}","source":script(s["actions"])})
    for t in spec.get("topics",[]):
        if not check_id(t["id"]):raise ValueError("invalid topic")
        for i,r in enumerate(t["responses"]):
            for phase in ("begin","end"):
                if r.get(phase):result.append({"slot":f"{t['id']}_{i+1}_{phase}","source":script(r[phase])})
    if len({r["slot"].casefold() for r in result})!=len(result):raise ValueError("duplicate script slot")
    return {"quest":q,"scripts":result,"compiled":False,"scope":"GECK result script source only; compile in editor against the actual plugin"}
def export(spec,folder):
    report=plan(spec);p=Path(folder);p.mkdir(parents=True,exist_ok=False)
    for r in report["scripts"]:(p/(r["slot"]+".txt")).write_text(r["source"],encoding="ascii")
    (p/"manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    return report
