"""Portable aliases and cinematic scene plan, validated independently of engine adapters."""
from .quest_editor import check_id
from collections import defaultdict
import math
def validate(p):
    if p.get("schema")!=1 or not check_id(p.get("id")):raise ValueError("invalid quest scene project")
    if set(p)-{"schema","id","aliases","scenes"}:raise ValueError("unknown project fields")
    aliases={};scenes=set();lines=[]
    for a in p.get("aliases",[]):
        if set(a)-{"id","kind","binding","optional"} or not check_id(a.get("id")) or a["id"].casefold() in aliases or a["kind"] not in {"actor","reference","location"} or type(a.get("optional",False)) is not bool:raise ValueError("invalid alias")
        b=a["binding"]
        if not isinstance(b,dict) or set(b)!={"plugin","id"} or not isinstance(b["plugin"],str) or not b["plugin"].lower().endswith((".esm",".esp",".esl")) or any(c in b["plugin"] for c in "/\\:") or type(b["id"]) is not int or not 0<b["id"]<=0xffffff:raise ValueError("invalid alias binding")
        aliases[a["id"].casefold()]=a
    for s in p.get("scenes",[]):
        if set(s)-{"id","phases"} or not check_id(s.get("id")) or s["id"].casefold() in scenes:raise ValueError("invalid scene")
        scenes.add(s["id"].casefold());last=-1
        for phase in s["phases"]:
            if set(phase)!={"index","actions"} or type(phase["index"]) is not int or not last<phase["index"]<=65535:raise ValueError("phases must be ascending")
            last=phase["index"];busy=defaultdict(list);ids=set()
            for a in phase["actions"]:
                if set(a)-{"id","actor","kind","start","duration","text","target"} or not check_id(a.get("id")) or a["id"].casefold() in ids:raise ValueError("invalid action")
                ids.add(a["id"].casefold());actor=aliases.get(a["actor"].casefold())
                if not actor or actor["kind"]!="actor":raise ValueError("action requires actor alias")
                start,duration=a["start"],a["duration"]
                if any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,duration)) or not 0<=start<=3600 or not 0<duration<=3600:raise ValueError("invalid action time")
                if any(start<end and start+duration>begin for begin,end in busy[a["actor"].casefold()]):raise ValueError("overlapping actions for actor in phase")
                busy[a["actor"].casefold()].append((start,start+duration))
                if a["kind"]=="dialogue":
                    if not isinstance(a.get("text"),str) or not a["text"] or "target" in a:raise ValueError("invalid dialogue action")
                    lines.append({"id":f'{p["id"]}.{s["id"]}.{last}.{a["id"]}',"actor":a["actor"],"text":a["text"]})
                elif a["kind"]=="move":
                    if a.get("target","").casefold() not in aliases or "text" in a:raise ValueError("invalid move target")
                elif a["kind"]!="wait" or set(a)&{"text","target"}:raise ValueError("unknown action kind")
    return {"valid":True,"aliases":len(aliases),"scenes":len(scenes),"lines":lines,"scope":"portable scene authoring; not native SCEN or QUST alias records"}
def timeline(p,scene):
    validate(p)
    matches=[s for s in p["scenes"] if s["id"]==scene]
    if len(matches)!=1:raise ValueError("unknown scene")
    offset=0;events=[]
    for phase in matches[0]["phases"]:
        for a in phase["actions"]:
            events.append({"phase":phase["index"],**a,"absolute_start":offset+a["start"],"absolute_end":offset+a["start"]+a["duration"]})
        offset+=max((a["start"]+a["duration"] for a in phase["actions"]),default=0)
    return {"scene":scene,"duration":offset,"actions":sorted(events,key=lambda a:(a["absolute_start"],a["id"]))}
