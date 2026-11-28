"""Read-only validation of expansion design data; no native game writes."""
import argparse
import json
from pathlib import Path

def indexed(rows,label):
    result={}
    for row in rows:
        key=row.get("id")
        if not isinstance(key,str) or not key or key in result:
            raise ValueError(f"{label}: missing or duplicate id {key!r}")
        result[key]=row
    return result

def validate(board):
    if board.get("schema")!="chimster.expansion-design.v1":
        raise ValueError("unsupported board schema")
    output={}
    for pid,p in indexed(board["projects"],"project").items():
        factions=indexed(p["factions"],pid+" factions")
        actors=indexed(p["actors"],pid+" actors")
        locations=indexed(p["locations"],pid+" locations")
        quests=indexed(p["quests"],pid+" quests")
        for aid,a in actors.items():
            if a["faction"] not in factions or a["home"] not in locations:
                raise ValueError(f"{pid}/{aid}: dangling faction or home")
        for qid,q in quests.items():
            if q["kind"] not in ("main","side") or not q["objective"] or not q["resolutions"]:
                raise ValueError(f"{pid}/{qid}: incomplete quest outline")
            for field,table in (("requires",quests),("locations",locations),("actors",actors)):
                if any(ref not in table for ref in q[field]):
                    raise ValueError(f"{pid}/{qid}: dangling {field}")
        pending=set(quests)
        order=[]
        done=set()
        while pending:
            ready=sorted(q for q in pending if set(quests[q]["requires"])<=done)
            if not ready: raise ValueError(f"{pid}: cyclic dependencies")
            order.extend(ready);done.update(ready);pending.difference_update(ready)
        if not p["initial_slice"] or any(loc not in locations for loc in p["initial_slice"]):
            raise ValueError(f"{pid}: invalid slice")
        main=[q for q in quests.values() if q["kind"]=="main"]
        if len([q for q in main if not q["requires"]])!=1:
            raise ValueError(f"{pid}: expected one main quest entry")
        output[pid]={"title":p["title"],"game":p["game"],"locations":len(locations),
            "actors":len(actors),"factions":len(factions),"main_quests":len(main),
            "side_quests":len(quests)-len(main),"slice_locations":p["initial_slice"],
            "quest_dependency_order":order,"status":"design only"}
    return output

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("board",type=Path,nargs="?",default=Path(__file__).with_name("campaign-board.json"))
    a=p.parse_args()
    print(json.dumps(validate(json.loads(a.board.read_text(encoding="utf-8"))),indent=2))

if __name__=="__main__":main()
