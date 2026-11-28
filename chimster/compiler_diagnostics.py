"""Normalize compiler diagnostics without losing original log lines."""
import re
from pathlib import PureWindowsPath

ANSI=re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
LOCATIONS=(
    re.compile(r"^(?P<file>.*?\.(?:psc|lua|txt|gek|geck|obscript|mwscript))\s*\((?P<line>\d+)\s*,\s*(?P<column>\d+)\)\s*:\s*(?P<message>.*)$",re.I),
    re.compile(r"^(?P<file>.*?\.(?:psc|lua|txt|gek|geck|obscript|mwscript)):(?P<line>\d+):(?:(?P<column>\d+):)?\s*(?P<message>.*)$",re.I),
    re.compile(r"^(?P<file>.*?\.(?:psc|lua|txt))\s*\((?P<line>\d+)\)\s*:\s*(?P<message>.*)$",re.I),
    re.compile(r"^(?:error\s+at\s+)?line\s+(?P<line>\d+)(?:\s*,\s*column\s+(?P<column>\d+))?\s*:\s*(?P<message>.*)$",re.I),
)
def parse(output, *, default_file=None, stream=None):
    result=[]
    for raw in output.splitlines():
        line=ANSI.sub("",raw).strip()
        if not line:continue
        # luac prefixes its messages with its executable name.
        line=re.sub(r"^(?:.*[\\/])?luac(?:5\.1|-5\.1|\.exe)?:\s*","",line,flags=re.I)
        location=None
        for pattern in LOCATIONS:
            match=pattern.match(line)
            if match:
                location=match.groupdict();break
        msg=location["message"] if location else line
        explicit=re.match(r"^(fatal(?: error)?|error|warning|note|info)\b(?:\s+[A-Z]\d+)?\s*:?\s*",msg,re.I)
        severity=("error" if explicit.group(1).lower().startswith("fatal") else explicit.group(1).lower()) if explicit else (
            "warning" if re.search(r"\bwarning\b",msg,re.I) and location else "error" if location else "info")
        item={"severity":severity,"message":msg,"raw":raw}
        if stream:item["stream"]=stream
        if location:
            name=location.get("file") or default_file
            if name:item["file"]=name
            item["line"]=int(location["line"])
            if location.get("column") is not None:item["column"]=int(location["column"])
        result.append(item)
    return result

def summarize(items):
    return {level:sum(x["severity"]==level for x in items) for level in ("error","warning","note","info")}

def navigation(item,source_path,source_text):
    """Never open a compiler-supplied path. Only navigate current saved source."""
    if not item.get("file") or not item.get("line"):return None
    norm=lambda s:str(s).replace("\\","/").casefold()
    actual=norm(source_path)
    # Absolute paths must match; basename-only diagnostics are allowed.
    reported=norm(item["file"])
    if reported!=actual and not ("/" not in reported and reported==actual.rsplit("/",1)[-1]):return None
    lines=source_text.split("\n")
    row=item["line"]
    if not 1<=row<=len(lines):return None
    # Column bases vary across compiler versions: navigate to the line start.
    return f"{row}.0"

def collect(report):
    items=list(report.get("diagnostics",[]))
    for row in report.get("results",[]):
        items.extend(collect(row.get("result",{})))
    return items


def remap(items,mapping):
    """Map only exact staged paths or unambiguous basenames to known source files."""
    norm=lambda p:str(p).replace("\\","/").casefold()
    exact={norm(k):v for k,v in mapping.items()}
    names={}
    for k,v in exact.items():names.setdefault(k.rsplit("/",1)[-1],[]).append(v)
    out=[]
    for item in items:
        item=dict(item)
        if item.get("file"):
            key=norm(item["file"])
            hit=exact.get(key)
            if hit is None and "/" not in key and len(names.get(key,[]))==1:hit=names[key][0]
            if hit:
                item["reported_file"]=item["file"];item["file"]=hit["path"]
                item["source_sha256"]=hit["sha256"]
        out.append(item)
    return out
