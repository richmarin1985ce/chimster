"""Skyrim quest/dialogue fragment wrapper drafts; does not bind VMAD fragments."""
from pathlib import Path
import re
import json
from .vmad import GAMES
from .script_lint import check
from .script_symbols import masked

IDENT=re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,254}")

def generate(game,script,kind,fragments):
    if game not in GAMES:raise ValueError("Skyrim-family fragment drafts only")
    if kind not in ("quest","dialogue") or not isinstance(script,str) or not IDENT.fullmatch(script):
        raise ValueError("unsupported fragment kind or script name")
    if not isinstance(fragments,list) or not 1<=len(fragments)<=256:raise ValueError("expected 1–256 fragment entries")
    parent="Quest" if kind=="quest" else "TopicInfo"
    lines=[f"Scriptname {script} Extends {parent} Hidden",""]
    manifest=[];seen=set();events=set()
    for row in fragments:
        if not isinstance(row,dict):raise ValueError("invalid fragment entry")
        name=row.get("function");event=row.get("event");body=row.get("body","")
        if not isinstance(name,str) or not IDENT.fullmatch(name) or not name.casefold().startswith("fragment_"):
            raise ValueError("explicit Creation Kit Fragment_ identifier required")
        if not isinstance(event,str) or not event.strip() or len(event)>256:raise ValueError("explicit owner/event label required")
        if name.casefold() in seen or event.casefold() in events:raise ValueError("duplicate fragment function or event")
        if not isinstance(body,str) or len(body)>8192 or "\0" in body:raise ValueError("invalid fragment body")
        seen.add(name.casefold());events.add(event.casefold())
        clean=masked(body,"papyrus")
        if re.search(r"(?im)^\s*(?:Scriptname|(?:\w+\s+)?Function|EndFunction|Event|EndEvent|State|EndState|Import|(?:\w+\s+)?Property|EndProperty)\b",clean):
            raise ValueError("fragment body must contain statements, not top-level declarations")
        if kind=="quest":
            lines.append(f"Function {name}()")
        else:
            lines.extend([f"Function {name}(ObjectReference akSpeakerRef)","    Actor akSpeaker = akSpeakerRef as Actor"])
        lines.extend("    "+line if line.strip() else "" for line in body.splitlines())
        lines.extend(["EndFunction",""])
        manifest.append({"event":event,"function":name})
    source="\n".join(lines)+"\n"
    result=check(source)
    if not result["valid"]:raise ValueError("fragment source block errors: "+str(result["issues"]))
    return {"game":game,"script":script,"kind":kind,"source":source,"bindings":manifest,
            "scope":"wrapper source draft only; Creation Kit fragment metadata and compiler/runtime verification required"}

def export(game,script,kind,fragments,output):
    report=generate(game,script,kind,fragments)
    p=Path(output)
    if p.name.casefold()!=(script+".psc").casefold():raise ValueError("PSC filename must match Scriptname")
    with p.open("x",encoding="utf-8") as stream:stream.write(report["source"])
    return {**report,"output":str(p)}
