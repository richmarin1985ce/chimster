"""Versioned portable translation catalogs, exact memory reuse and guarded application."""
import copy,hashlib,json,re
from .localization_audit import audit
from .localization import TranslationMemory
from .books import Book
from .quest_editor import validate as validate_quest
LANG=re.compile(r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8}){0,4}")
TEXT_FIELDS={"FACT":("title",),"MISC":("title",),"REPU":("title",),"CONT":("title",),"AMMO":("title","short_name","abbreviation"),"CLAS":("title","description"),"PERK":("title","description"),"SPEL":("title",),"ALCH":("title",),"KEYM":("title",),"NPC_":("title",),"WEAP":("title",),"ARMO":("title",),"RACE":("title",),"MGEF":("title","description")}
def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode("utf-8")).hexdigest()
def fields(kind,project):
    """Yield stable ID, field path, source. Never translate identifiers or model paths."""
    if not isinstance(project,dict) or project.get("schema")!=1:raise ValueError("unsupported source schema")
    if kind=="book":
        b=Book(**{k:v for k,v in project.items() if k!="schema"}).validate()
        yield b.editor_id+".title",["title"],b.title
        yield b.editor_id+".author",["author"],b.author
        for i,t in enumerate(b.pages):yield f"{b.editor_id}.page.{i+1:04d}",["pages",i],t
    elif kind=="quest":
        validate_quest(project)
        for i,n in enumerate(project["nodes"]):
            yield project["id"]+"."+n["id"]+".text",["nodes",i,"text"],n["text"]
            for j,e in enumerate(n.get("choices",[])):
                yield project["id"]+"."+n["id"]+"."+e["id"],["nodes",i,"choices",j,"text"],e["text"]
    elif kind=="records":
        for i,r in enumerate(project["records"]):
            f=r["fields"];base=r["id"]
            for k in TEXT_FIELDS.get(r["type"],()):
                if k in f:yield base+"."+k,["records",i,"fields",k],f[k]
            if r["type"]=="FACT":
                for j,rank in enumerate(f.get("ranks",[])):
                    for k in ("male","female"):yield f"{base}.rank.{rank['rank']}.{k}",["records",i,"fields","ranks",j,k],rank[k]
    elif kind=="native-quest":
        base=project["id"];yield base+".title",["title"],project["title"]
        for i,s in enumerate(project["stages"]):yield f"{base}.stage.{s['index']}",["stages",i,"log"],s["log"]
        for i,o in enumerate(project.get("objectives",[])):yield f"{base}.objective.{o['index']}",["objectives",i,"text"],o["text"]
        for i,t in enumerate(project.get("topics",[])):
            prefix=base+"."+t["id"];yield prefix+".prompt",["topics",i,"prompt"],t["prompt"]
            for j,r in enumerate(t["responses"]):
                if not isinstance(r.get("id"),str) or not r["id"]:raise ValueError("native response requires stable id for localization")
                key=prefix+"."+r["id"];path=["topics",i,"responses",j]
                for k in ("text","prompt"):
                    if k in r:yield key+"."+k,path+[k],r[k]
                for n,line in enumerate(r.get("lines",[])):yield f"{key}.line.{n+1}",path+["lines",n,"text"],line["text"]
    else:raise ValueError("unsupported source kind")
def catalog(kind,project,source_lang,target_lang):
    if not all(isinstance(v,str) and LANG.fullmatch(v) for v in (source_lang,target_lang)) or source_lang.casefold()==target_lang.casefold():raise ValueError("invalid language pair")
    entries={}
    for key,path,value in fields(kind,project):
        if key in entries or not isinstance(value,str) or "\0" in value:raise ValueError("duplicate ID or invalid text")
        entries[key]={"source":value,"target":"" if not value else None,"context":kind+":"+key}
    return {"schema":1,"kind":kind,"source_lang":source_lang,"target_lang":target_lang,"source_sha256":digest(project),"entries":entries}
def verified(c,project):
    expected=catalog(c["kind"],project,c["source_lang"],c["target_lang"])
    if c.get("schema")!=1 or c.get("source_sha256")!=expected["source_sha256"] or set(c["entries"])!=set(expected["entries"]):raise ValueError("catalog source changed")
    for k,e in c["entries"].items():
        if any(e.get(f)!=expected["entries"][k][f] for f in ("source","context")):raise ValueError("catalog entry changed")
        if e.get("target") is not None and (not isinstance(e["target"],str) or "\0" in e["target"]):raise ValueError("invalid translation")
    return c
def reuse(c,project,memory):
    c=copy.deepcopy(verified(c,project));count=0
    for e in c["entries"].values():
        if e["target"] is None:
            v=memory.lookup(c["source_lang"],c["target_lang"],e["context"],e["source"])
            if v is not None and audit(e["source"],v)["ok"]:e["target"]=v;count+=1
    return c,count
def check(c,project,encoding="utf-8",terms=None):
    verified(c,project);issues=[]
    if encoding not in {"utf-8","cp1252"}:raise ValueError("unsupported encoding")
    if terms is not None and (not isinstance(terms,dict) or any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in terms.items())):raise ValueError("invalid glossary")
    for key,e in c["entries"].items():
        v=e["target"]
        if v is None:issues.append({"id":key,"status":"untranslated"});continue
        if e["source"] and not v.strip():issues.append({"id":key,"status":"empty"})
        if not audit(e["source"],v)["ok"]:issues.append({"id":key,"status":"placeholder-mismatch"})
        try:v.encode(encoding)
        except UnicodeEncodeError:issues.append({"id":key,"status":"encoding"})
        for source,target in (terms or {}).items():
            if source.casefold() in e["source"].casefold() and target.casefold() not in v.casefold():issues.append({"id":key,"status":"terminology-advisory","term":source})
    return {"valid":not any(i["status"]!="terminology-advisory" for i in issues),"entries":len(c["entries"]),"issues":issues}
def apply(c,project,encoding="utf-8"):
    report=check(c,project,encoding)
    if not report["valid"]:raise ValueError("translation validation failed: "+str(report["issues"][:5]))
    result=copy.deepcopy(project)
    for key,path,_ in fields(c["kind"],project):
        obj=result
        for p in path[:-1]:obj=obj[p]
        obj[path[-1]]=c["entries"][key]["target"]
    return result
def remember(c,project,memory,encoding="utf-8"):
    if not check(c,project,encoding)["valid"]:raise ValueError("invalid catalog")
    for e in c["entries"].values():memory.remember(c["source_lang"],c["target_lang"],e["context"],e["source"],e["target"])
    return len(c["entries"])
