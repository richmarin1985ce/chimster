"""Stable localization catalogs and review-only translation memory reuse."""
from pathlib import Path
from copy import deepcopy
import json,re
from .localization import TranslationMemory
from .localization_audit import audit
from .project import read_json
LANG=re.compile(r"[A-Za-z][A-Za-z0-9-]{1,34}")
def catalog(kind,source):
    if kind=="book":
        from .books import load
        b=load(source);strings=b.localization()
    elif kind=="quest":
        from .quest_editor import validate
        p=read_json(Path(source));r=validate(p)
        if not r["valid"]:raise ValueError("invalid quest")
        strings=r["localization"]
    elif kind in {"native-quest","records"}:
        from .localization_fields import extract
        strings={k:v for k,v,_ in extract(kind,read_json(Path(source)))}
    elif kind=="strings":
        p=read_json(Path(source))
        if not isinstance(p,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in p.items()):raise ValueError("expected string dictionary")
        strings=p
    else:raise ValueError("unknown catalog type")
    if len(strings)>100000:raise ValueError("catalog too large")
    return {"schema":1,"kind":kind,"entries":[{"id":k,"source":v,"context":kind+":"+k,"target":None,"status":"untranslated"} for k,v in sorted(strings.items())]}
def validate(c):
    if c.get("schema")!=1 or c.get("kind") not in {"book","quest","strings","native-quest","records"}:raise ValueError("invalid catalog")
    rows=c["entries"];seen=set()
    if not isinstance(rows,list) or len(rows)>100000:raise ValueError("catalog exceeds limit")
    for r in rows:
        k=r["id"]
        if not isinstance(k,str) or not k or len(k)>512 or k in seen or r["context"]!=c["kind"]+":"+k:raise ValueError("invalid or duplicate string ID")
        seen.add(k)
        for v in (r["source"],r["target"]):
            if v is not None and (not isinstance(v,str) or len(v)>256000 or "\0" in v):raise ValueError("invalid text")
        if not isinstance(r["source"],str) or r["status"] not in {"untranslated","suggested","approved"} or (r["target"] is None)!=(r["status"]=="untranslated"):raise ValueError("invalid translation state")
    return c
def suggest(c,db,src,dst,reuse_unambiguous=False):
    validate(c)
    if not all(isinstance(v,str) and LANG.fullmatch(v) for v in (src,dst)) or src.casefold()==dst.casefold():raise ValueError("invalid language pair")
    out=deepcopy(c);out["src_lang"]=src;out["dst_lang"]=dst
    if c.get("src_lang",src)!=src or c.get("dst_lang",dst)!=dst:raise ValueError("catalog language mismatch")
    memory=TranslationMemory(Path(db))
    try:
        for r in out["entries"]:
            if r["status"]!="untranslated":continue
            t=memory.lookup(src,dst,r["context"],r["source"])
            if t is None and reuse_unambiguous:
                rows=memory.db.execute("SELECT DISTINCT target FROM memory WHERE src_lang=? AND dst_lang=? AND source=? LIMIT 2",(src,dst,r["source"])).fetchall()
                if len(rows)==1:t=rows[0][0]
            if t is not None and audit(r["source"],t)["ok"]:r["target"]=t;r["status"]="suggested"
    finally:memory.close()
    return out
def review(c,encoding="utf-8"):
    validate(c);issues=[];approved=0
    for r in c["entries"]:
        if r["status"]!="approved":issues.append({"id":r["id"],"issue":"not approved"});continue
        a=audit(r["source"],r["target"])
        if not a["ok"]:issues.append({"id":r["id"],"issue":"placeholder mismatch","detail":a});continue
        try:r["target"].encode(encoding)
        except UnicodeEncodeError:issues.append({"id":r["id"],"issue":"encoding mismatch"});continue
        approved+=1
    return {"valid":not issues,"approved":approved,"total":len(c["entries"]),"issues":issues}
def remember(c,db):
    if not review(c)["valid"]:raise ValueError("approve and validate all strings before storing")
    src,dst=c["src_lang"],c["dst_lang"]
    if not all(isinstance(v,str) and LANG.fullmatch(v) for v in (src,dst)) or src.casefold()==dst.casefold():raise ValueError("invalid language pair")
    m=TranslationMemory(Path(db))
    try:
        with m.db:
            m.db.executemany("INSERT INTO memory VALUES(?,?,?,?,?) ON CONFLICT(src_lang,dst_lang,context,source) DO UPDATE SET target=excluded.target",[(src,dst,r["context"],r["source"],r["target"]) for r in c["entries"]])
    finally:m.close()
    return {"stored":len(c["entries"])}
def apply(c,source,output,encoding="utf-8"):
    if not review(c,encoding)["valid"]:raise ValueError("catalog requires approved compatible translations")
    original=catalog(c["kind"],source)
    if {r["id"]:r["source"] for r in original["entries"]}!={r["id"]:r["source"] for r in c["entries"]}:raise ValueError("source strings changed; regenerate catalog")
    values={r["id"]:r["target"] for r in c["entries"]}
    p=Path(output)
    if c["kind"]=="book":
        from .books import load,save
        save(load(source).translated(values),p)
    elif c["kind"]=="quest":
        from .quest_editor import save
        q=read_json(Path(source))
        for n in q["nodes"]:
            key=q["id"]+"."+n["id"]+"."
            n["text"]=values[key+"text"]
            for e in n.get("choices",[]):e["text"]=values[key+e["id"]]
        save(q,p)
    elif c["kind"] in {"native-quest","records"}:
        from .localization_fields import replace
        save_json(replace(c["kind"],read_json(Path(source)),values),p)
    else:save_json(values,p)
    return {"output":str(p),"strings":len(values)}
def save_json(value,path):
    with Path(path).open("x",encoding="utf-8") as f:json.dump(value,f,ensure_ascii=False,indent=2)
def pack_native(table,output,kind,encoding):
    from .formats import encode_strings,decode_strings
    values=read_json(Path(table));entries={}
    for k,v in values.items():
        if not re.fullmatch(r"0|[1-9][0-9]{0,9}",k) or int(k)>0xffffffff or not isinstance(v,str):raise ValueError("numeric string IDs required")
        entries[int(k)]=v
    blob=encode_strings(entries,kind,encoding)
    if decode_strings(blob,kind,encoding)!=entries:raise ValueError("string table roundtrip mismatch")
    with Path(output).open("xb") as f:f.write(blob)
    return {"output":str(output),"strings":len(entries),"format":kind,"encoding":encoding}
