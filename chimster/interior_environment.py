"""Portable per-room lighting and acoustic environment, not native game field serialization."""
from math import isfinite,dist
from .interior_layout import bounds,contains,point,validate
from collections import deque

def number(v,lo,hi):
    if type(v) not in (float,int) or not isfinite(v) or not lo<=v<=hi:raise ValueError("environment value out of range")
    return float(v)
def color(v):
    if not isinstance(v,(tuple,list)) or len(v)!=3:raise ValueError("RGB required")
    return tuple(number(x,0,1) for x in v)
def inspect(layout,environment):
    if not validate(layout)["valid"]:raise ValueError("invalid layout")
    if not isinstance(environment,dict) or set(environment)-{"rooms","lights"}:raise ValueError("invalid environment")
    rooms={r["id"]:bounds(r) for r in layout["rooms"]};settings={}
    for rid,row in environment.get("rooms",{}).items():
        if rid not in rooms or set(row)-{"ambient","fog_color","fog_near","fog_far","reverb","absorption"}:raise ValueError("invalid room environment")
        near=number(row.get("fog_near",0),0,1e7);far=number(row.get("fog_far",1e7),0,1e7)
        if far<=near:raise ValueError("fog far must exceed near")
        settings[rid]={"ambient":color(row.get("ambient",[.2,.2,.2])),"fog_color":color(row.get("fog_color",[0,0,0])),
                       "fog_near":near,"fog_far":far,"reverb":number(row.get("reverb",0),0,1),
                       "absorption":number(row.get("absorption",0),0,1)}
    lights=[];seen=set()
    for light in environment.get("lights",[]):
        if set(light)!={"id","room","position","color","radius","intensity"} or light["id"] in seen:raise ValueError("invalid light")
        seen.add(light["id"]);rid=light["room"];pos=point(light["position"])
        if rid not in rooms or not contains(rooms[rid],pos):raise ValueError("light outside owning room")
        lights.append({**light,"position":pos,"color":color(light["color"]),"radius":number(light["radius"],.001,1e7),
                       "intensity":number(light["intensity"],0,100)})
    return settings,lights

def sample(layout,environment,room,position,closed=()):
    settings,lights=inspect(layout,environment);p=point(position)
    boxes={r["id"]:bounds(r) for r in layout["rooms"]}
    if room not in boxes or not contains(boxes[room],p):raise ValueError("listener outside room")
    rgb=list(settings.get(room,{}).get("ambient",(.2,.2,.2)))
    for light in lights:
        if light["room"]!=room:continue
        gain=max(0.,1-dist(p,light["position"])/light["radius"])**2*light["intensity"]
        for i,c in enumerate(light["color"]):rgb[i]+=gain*c
    blocked=set(closed);graph={r:set() for r in boxes}
    if not blocked<={p["id"] for p in layout.get("portals",[])}:raise ValueError("unknown closed portal")
    for portal in layout.get("portals",[]):
        if portal["id"] not in blocked:
            a,b=portal["rooms"];graph[a].add(b);graph[b].add(a)
    # Bounded best-path scalar attenuation for preview, not acoustical simulation.
    gains={room:1.};queue=deque([room])
    while queue:
        a=queue.popleft()
        for b in graph[a]:
            gain=gains[a]*.5*(1-settings.get(b,{}).get("absorption",0))
            if gain>gains.get(b,0)+1e-9:gains[b]=gain;queue.append(b)
    return {"rgb":tuple(min(1,v) for v in rgb),"acoustic_gain":gains,
            "reverb":settings.get(room,{}).get("reverb",0),"scope":"portable light and acoustic preview; no native engine lighting or DSP"}
