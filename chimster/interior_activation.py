"""Portable activation chains: explicit events, finite acyclic dispatch, no game script execution."""
from collections import defaultdict,deque
from .interior_runtime import Triggers

def plan(layout,chains,door_ids):
    triggers={t["id"] for t in layout.get("triggers",[])};doors=set(door_ids)
    if not isinstance(chains,list) or len(chains)>10000:raise ValueError("invalid activation chains")
    routes=defaultdict(list);graph=defaultdict(set);count=0
    for route in chains:
        if set(route)!={"event","actions"}:raise ValueError("invalid activation route")
        event=route["event"]
        if not isinstance(event,str) or not event:raise ValueError("invalid event")
        if not isinstance(route["actions"],list) or len(route["actions"])>64:raise ValueError("invalid action list")
        for a in route["actions"]:
            count+=1
            if count>100000:raise ValueError("action limit")
            if a.get("op")=="door":
                if set(a)!={"op","target","open"} or a["target"] not in doors or type(a["open"]) is not bool:raise ValueError("invalid door action")
            elif a.get("op")=="emit":
                if set(a)!={"op","target"} or not isinstance(a["target"],str) or not a["target"]:raise ValueError("invalid emitted event")
                graph[event].add(a["target"])
            else:raise ValueError("unknown activation action")
            routes[event].append(dict(a))
    nodes=set(routes)|{n for v in graph.values() for n in v};indegree={n:0 for n in nodes}
    for targets in graph.values():
        for n in targets:indegree[n]+=1
    q=deque(n for n in nodes if not indegree[n]);visited=0
    while q:
        n=q.popleft();visited+=1
        for v in graph[n]:
            indegree[v]-=1
            if not indegree[v]:q.append(v)
    if visited!=len(nodes):raise ValueError("cyclic activation chain")
    return dict(routes)

class ActivationPreview:
    def __init__(self,layout,chains,door_ids):
        self.routes=plan(layout,chains,door_ids);self.triggers=Triggers(layout);self.doors={d:True for d in door_ids}
    def dispatch(self,events,budget=4096):
        if not 1<=budget<=100000:raise ValueError("invalid dispatch budget")
        pending=deque(events);state=dict(self.doors);trace=[];steps=0
        while pending:
            event=pending.popleft();steps+=1
            if steps>budget:raise ValueError("activation budget exhausted; no door state committed")
            for a in self.routes.get(event,[]):
                steps+=1
                if steps>budget:raise ValueError("activation budget exhausted; no door state committed")
                trace.append({"event":event,**a})
                if a["op"]=="emit":pending.append(a["target"])
                else:state[a["target"]]=a["open"]
        self.doors=state
        return {"doors":dict(state),"trace":trace,"scope":"portable activation preview"}
    def update(self,position,budget=4096):
        previous=set(self.triggers.inside)
        try:
            events=self.triggers.update(position)
            result=self.dispatch([e["event"]+":"+e["phase"] for e in events],budget)
        except Exception:
            self.triggers.inside=previous;raise
        return {**result,"trigger_events":events}
    def closed_portals(self,bindings):
        return sorted(pid for pid,did in bindings.items() if self.doors.get(did) is False)
