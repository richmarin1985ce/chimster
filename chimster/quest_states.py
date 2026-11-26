"""Bounded exact exploration of the portable boolean quest model."""
from collections import deque
from .quest_editor import validate
def analyze(project,max_states=100000):
    if type(max_states) is not int or not 1<=max_states<=200000:raise ValueError("invalid state budget")
    graph=validate(project)
    nodes={n["id"]:n for n in project["nodes"]}
    start=(project["start"],frozenset())
    queue=deque([start]);seen={start};reverse={};terminal=set();dead=[];complete=True
    while queue:
        state=queue.popleft();stage,flags=state;edges=nodes[stage].get("choices",[])
        if not edges:terminal.add(state);continue
        enabled=[e for e in edges if all((k in flags)==v for k,v in e.get("requires",{}).items())]
        if not enabled:dead.append(state)
        for e in enabled:
            new=set(flags)
            for k,v in e.get("sets",{}).items():
                if v:new.add(k)
                else:new.discard(k)
            target=(e["target"],frozenset(new))
            if target not in seen:
                if len(seen)>=max_states:complete=False;continue
                seen.add(target);queue.append(target)
            reverse.setdefault(target,set()).add(state)
    finish=set(terminal);queue=deque(finish)
    while queue:
        for p in reverse.get(queue.popleft(),()):
            if p not in finish:finish.add(p);queue.append(p)
    def row(s):return {"stage":s[0],"true_flags":sorted(s[1])}
    def order(s):return (s[0],tuple(sorted(s[1])))
    return {"complete":complete,"valid":complete and graph["valid"] and seen==finish,
      "states":len(seen),"terminal_states":len(terminal),"deadlocks":[row(s) for s in sorted(dead,key=order)[:100]],
      "no_exit_count":len(seen-finish) if complete else None,
      "no_exit_examples":[row(s) for s in sorted(seen-finish,key=order)[:100]] if complete else [],
      "unreachable_stages":sorted(set(nodes)-{s[0] for s in seen}) if complete else [],
      "scope":"exact for portable boolean flags from all-false initial state if complete; not native engine semantics"}
