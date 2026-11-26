"""Advisory translation placeholder/markup audit. No automatic rewriting."""
from collections import Counter
import re
TOKENS=re.compile(r'%%|%(?:\d+\$)?[-+0 #]*(?:\d+|\*)?(?:\.\d+)?[sdifuxX]|(?<!\{)\{(?:\d+|[A-Za-z_]\w*)(?:![rsa])?(?::[^{}]+)?\}(?!\})|</?[A-Za-z][^<>]*>|\\[nrt]|[\r\n]')
def placeholders(text):
    return Counter(TOKENS.findall(text))
def audit(source,target):
    missing=placeholders(source)-placeholders(target)
    extra=placeholders(target)-placeholders(source)
    return {"missing":dict(missing),"extra":dict(extra),"ok":not missing and not extra,"warning":"Heuristic checks only; game-specific substitution/markup grammar may differ."}
def audit_tables(source,target):
    result=[]
    for key in sorted(set(source)|set(target)):
        if key not in source:result.append({"id":key,"status":"extra-id"})
        elif key not in target:result.append({"id":key,"status":"missing-id"})
        else:
            report=audit(source[key],target[key])
            if not report["ok"]:result.append({"id":key,"status":"placeholder-mismatch",**report})
    return result
