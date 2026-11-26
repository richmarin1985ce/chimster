"""Portable branching quest/dialogue graph with static validation and preview."""
from pathlib import Path
from collections import deque
import re,json
ID=re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")
def check_id(v):
    return isinstance(v,str) and ID.fullmatch(v) is not None
def validate(p):
    if not isinstance(p,dict) or p.get("schema")!=1 or not check_id(p.get("id")):raise ValueError("invalid quest schema/id")
    nodes=p["nodes"]
    if not isinstance(nodes,list) or not 1<=len(nodes)<=2000:raise ValueError("invalid stage count")
    index={};strings={}
    for n in nodes:
        id=n["id"]
        if not check_id(id) or id in index or not isinstance(n["text"],str) or len(n["text"])>16000:raise ValueError("invalid or duplicate stage")
        index[id]=n;strings[p["id"]+"."+id+".text"]=n["text"]
    if p["start"] not in index:raise ValueError("missing start")
    reverse={k:[] for k in index};terminals=set()
    for id,n in index.items():
        edges=n.get("choices",[])
        if not isinstance(edges,list) or len(edges)>64:raise ValueError("invalid choices")
        if not edges:terminals.add(id)
        ids=set()
        for e in edges:
            eid=e["id"];target=e["target"]
            if not check_id(eid) or eid in ids or target not in index or not isinstance(e["text"],str) or len(e["text"])>4000:raise ValueError("invalid choice or target")
            ids.add(eid);reverse[target].append(id);strings[p["id"]+"."+id+"."+eid]=e["text"]
            for key in ("requires","sets"):
                cond=e.get(key,{})
                if not isinstance(cond,dict) or len(cond)>64 or any(not check_id(k) or type(v) is not bool for k,v in cond.items()):raise ValueError("flags must be named booleans")
    reachable={p["start"]};queue=deque(reachable)
    while queue:
        for e in index[queue.popleft()].get("choices",[]):
            if e["target"] not in reachable:reachable.add(e["target"]);queue.append(e["target"])
    can_finish=set(terminals);queue=deque(terminals)
    while queue:
        for k in reverse[queue.popleft()]:
            if k not in can_finish:can_finish.add(k);queue.append(k)
    return {"valid":len(reachable)==len(index) and len(can_finish)==len(index),"unreachable":sorted(set(index)-reachable),"no_structural_exit":sorted(set(index)-can_finish),"terminal_stages":sorted(terminals),"localization":strings,"scope":"structural graph only; conditions may still make endings unreachable"}
class Preview:
    def __init__(self,p):
        if not validate(p)["valid"]:raise ValueError("invalid quest graph")
        self.nodes={n["id"]:n for n in p["nodes"]};self.stage=p["start"];self.flags={};self.history=[]
    def choices(self):
        return [e for e in self.nodes[self.stage].get("choices",[]) if all(self.flags.get(k,False)==v for k,v in e.get("requires",{}).items())]
    def choose(self,id):
        matches=[e for e in self.choices() if e["id"]==id]
        if len(matches)!=1:raise ValueError("unavailable choice")
        e=matches[0];self.history.append((self.stage,dict(self.flags)));self.flags.update(e.get("sets",{}));self.stage=e["target"]
    def undo(self):
        if self.history:self.stage,self.flags=self.history.pop()
    def state(self):
        return {"stage":self.stage,"text":self.nodes[self.stage]["text"],"flags":dict(self.flags),"choices":self.choices()}
def load(path):
    p=Path(path)
    if p.stat().st_size>8*1024*1024:raise ValueError("quest file too large")
    return json.loads(p.read_text(encoding="utf-8"))
def save(p,path):
    if not validate(p)["valid"]:raise ValueError("invalid quest")
    with Path(path).open("x",encoding="utf-8") as f:json.dump(p,f,ensure_ascii=False,indent=2)
