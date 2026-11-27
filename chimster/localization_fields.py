"""Extract explicitly supported human-facing fields; keep every other field intact."""
from copy import deepcopy
from .quest_editor import check_id
def extract(kind,p):
    if p.get("schema")!=1:raise ValueError("unknown schema")
    rows=[];ids=set()
    def add(key,path,obj,field):
        if field not in obj:return
        if key in ids or not isinstance(obj[field],str):raise ValueError("duplicate localization ID or invalid text")
        ids.add(key);rows.append((key,obj[field],(*path,field)))
    if kind=="records":
        for i,r in enumerate(p["records"]):
            if not check_id(r["id"]):raise ValueError("invalid record ID")
            for k in ("title","description","short_name","abbreviation"):
                add(r["id"]+"."+k,("records",i,"fields"),r["fields"],k)
            for j,rank in enumerate(r["fields"].get("ranks",[])):
                n=rank["rank"]
                if type(n) is not int:raise ValueError("invalid rank")
                for k in ("male","female"):
                    add(f'{r["id"]}.rank.{n}.{k}',("records",i,"fields","ranks",j),rank,k)
    elif kind=="native-quest":
        q=p["id"]
        if not check_id(q):raise ValueError("invalid quest ID")
        add(q+".title",(),p,"title")
        for i,s in enumerate(p["stages"]):
            n=s["index"]
            if type(n) is not int:raise ValueError("invalid stage")
            add(f"{q}.stage.{n}.log",("stages",i),s,"log")
        for i,o in enumerate(p.get("objectives",[])):
            n=o["index"]
            if type(n) is not int:raise ValueError("invalid objective")
            add(f"{q}.objective.{n}.text",("objectives",i),o,"text")
        for i,t in enumerate(p.get("topics",[])):
            if not check_id(t["id"]):raise ValueError("invalid topic")
            k=q+".topic."+t["id"];base=("topics",i)
            add(k+".prompt",base,t,"prompt")
            for j,r in enumerate(t["responses"]):
                id=r.get("id")
                if not check_id(id):raise ValueError("localization requires stable explicit response IDs")
                prefix=k+".response."+id;path=(*base,"responses",j)
                for field in ("text","prompt"):add(prefix+"."+field,path,r,field)
                for n,line in enumerate(r.get("lines",[])):
                    add(prefix+f".line.{n+1}.text",(*path,"lines",n),line,"text")
    else:raise ValueError("unsupported kind")
    return rows
def replace(kind,project,values):
    result=deepcopy(project)
    rows=extract(kind,result)
    if set(values)!={k for k,_,_ in rows}:raise ValueError("localization IDs mismatch")
    for key,_,path in rows:
        obj=result
        for k in path[:-1]:obj=obj[k]
        obj[path[-1]]=values[key]
    return result
