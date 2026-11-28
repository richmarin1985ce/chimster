"""Read-only Papyrus runtime log analysis. Not an attached debugger."""
import re
from pathlib import Path
from collections import Counter

STAMP=re.compile(r"^\[(?P<time>[^\]]{1,64})\]\s*(?P<message>.*)$")
FRAME=re.compile(r"^\s*\[?(?P<object>.*?)\]?\.(?P<function>[A-Za-z_][\w]*)\(\)\s*-\s*\"(?P<file>[^\"\r\n]+\.psc)\"\s+Line\s+(?P<line>\d+)",re.I)
LEVEL=re.compile(r"^(?:error|warning|fatal(?: error)?|info)\s*:",re.I)
MAX_BYTES=16*1024*1024

def analyze(text):
    if len(text)>MAX_BYTES:raise ValueError("runtime log limit")
    events=[];current=None;counts=Counter()
    for raw in text.splitlines():
        m=STAMP.match(raw)
        if m:
            message=m["message"]
            level=LEVEL.match(message)
            if level:
                severity=level.group().rstrip(":").casefold()
                if severity.startswith("fatal"):severity="error"
            else:severity="info"
            current={"timestamp":m["time"],"severity":severity,"message":message,"frames":[]}
            events.append(current);counts[severity]+=1
        elif current:
            frame=FRAME.match(raw)
            if frame:
                f=frame.groupdict()
                f["line"]=int(f["line"])
                current["frames"].append(f)
            else:
                current.setdefault("continuation",[]).append(raw)
        elif raw.strip():
            current={"timestamp":None,"severity":"info","message":raw,"frames":[]}
            events.append(current);counts["info"]+=1
    repeated=Counter(e["message"] for e in events if e["severity"] in {"error","warning"})
    return {"counts":dict(counts),"events":events,
            "repeated":[{"message":m,"count":n} for m,n in repeated.most_common(50) if n>1],
            "scope":"offline log parsing; no VM state, breakpoints, or live game attachment"}

def inspect(path):
    p=Path(path)
    if p.stat().st_size>MAX_BYTES:raise ValueError("runtime log limit")
    with p.open("rb") as stream:data=stream.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise ValueError("runtime log limit")
    return analyze(data.decode("utf-8-sig",errors="replace"))
