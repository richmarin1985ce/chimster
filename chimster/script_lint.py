"""Advisory Papyrus structural checks, not a compiler."""
from pathlib import Path
import re
def check(source):
    if not isinstance(source,str) or len(source)>2*1024*1024:raise ValueError("script exceeds limit")
    # Remove line/block comments and strings while preserving line numbers.
    clean=re.sub(r';/[\s\S]*?/;|"(?:\\.|[^"\\])*"|;[^\n]*',lambda m:"".join("\n" if c=="\n" else " " for c in m.group()),source)
    stack=[];issues=[];declarations=[]
    for n,line in enumerate(clean.splitlines(),1):
        line=line.strip()
        if not line:continue
        words=line.casefold().split();first=words[0]
        if first=="scriptname":
            if len(words)<2:issues.append({"line":n,"message":"Missing script name"})
            else:declarations.append(words[1])
        if first in {"if","while","event","state"} or first=="auto" and len(words)>1 and words[1]=="state":
            stack.append(("state" if first=="auto" else first,n))
        elif first=="function" or re.match(r'^[a-z_]\w*(?:\[\])?\s+function\b',line,re.I):
            # Native declarations have no body.
            if not re.search(r'\bnative\b',line,re.I):stack.append(("function",n))
        elif first in {"elseif","else"}:
            if not stack or stack[-1][0]!="if":issues.append({"line":n,"message":first+" outside If"})
        elif first in {"endif","endwhile","endevent","endstate","endfunction"}:
            wanted=first[3:]
            if not stack or stack[-1][0]!=wanted:issues.append({"line":n,"message":"Unexpected "+first})
            else:stack.pop()
    for name,n in stack:issues.append({"line":n,"message":"Unclosed "+name})
    if len(declarations)!=1:issues.append({"line":1,"message":"Expected one Scriptname declaration"})
    return {"valid":not issues,"issues":issues,"script_names":declarations,"scope":"advisory lexical block checks only; multiline/native syntax and semantics require compiler"}
def check_file(path):
    p=Path(path)
    if p.stat().st_size>2*1024*1024:raise ValueError("script too large")
    return check(p.read_text(encoding="utf-8-sig"))
