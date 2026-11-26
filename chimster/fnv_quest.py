"""Experimental FNV quest and dialogue record fixture writer.
Optional verified dependencies; no compiled scripts or engine certification."""
from pathlib import Path
import struct,math
from .fnv_patch import sub,record
from .fnv_world import group,cstr
from .fnv_content import ident
from .fnv_records import scan,HEADER,subs
from .quest_editor import check_id

def u32(n):return struct.pack("<I",n)
def string(s,maxlen=4096):
    if not isinstance(s,str) or len(s)>maxlen:raise ValueError("invalid quest text length")
    return cstr(s)
def empty_script(source=""):
    return sub(b"SCHR",bytes(20))+sub(b"SCDA",b"")+sub(b"SCTX",source.encode("ascii"))
def conditions(rows,qid,stages,bindings=None):
    if not isinstance(rows,list) or len(rows)>64:raise ValueError("invalid conditions")
    out=[]
    for c in rows:
        if set(c)=={"reputation","axis","operator","value"}:
            if bindings is None or c["axis"] not in {"fame","infamy"} or c["operator"] not in {"eq","ne","gt","ge","lt","le"} or type(c["value"]) not in (int,float) or not math.isfinite(c["value"]) or not 0<=c["value"]<=1:raise ValueError("invalid reputation percentage condition")
            fid=bindings.resolve(c["reputation"],{"REPU"})
            op={"eq":0,"ne":0x20,"gt":0x40,"ge":0x60,"lt":0x80,"le":0xa0}[c["operator"]]
            out.append(sub(b"CTDA",struct.pack("<B3xfIIIII",op,c["value"],574,fid,int(c["axis"]=="fame"),0,0)))
            continue
        if set(c)=={"actor","is"} or set(c)=={"faction","member"}:
            actor="actor" in c;key="actor" if actor else "faction";flag=c["is" if actor else "member"]
            if bindings is None or type(flag) is not bool:raise ValueError("invalid dependency condition")
            ref=bindings.resolve(c[key],{"NPC_","CREA"} if actor else {"FACT"})
            out.append(sub(b"CTDA",struct.pack("<B3xfIIIII",0,float(flag),72 if actor else 71,ref,0,0,0)))
            continue
        if set(c)!={"stage","done"} or type(c["stage"]) is not int or c["stage"] not in stages or type(c["done"]) is not bool:raise ValueError("unsupported stage condition")
        # GetStageDone(current quest, stage) == 1/0, subject, no reference.
        out.append(sub(b"CTDA",struct.pack("<B3xfIIIII",0,float(c["done"]),59,qid,c["stage"],0,0)))
    return b"".join(out)
def export(spec,output,masters=(),allocator=None,script_draft=False):
    from .quest_scripts import plan
    scripts={v["slot"]:v["source"] for v in plan(spec)["scripts"]}
    if scripts and not script_draft:raise ValueError("authored scripts require explicit script-draft export and GECK compilation")
    from .fnv_bindings import Bindings
    bindings=Bindings(masters,output)
    if spec.get("schema")!=1 or not check_id(spec.get("id")):raise ValueError("invalid native quest specification")
    if set(spec)-{"schema","id","title","priority","stages","objectives","topics","start_enabled"}:raise ValueError("unsupported native quest fields")
    p=Path(output)
    if p.suffix.lower()!=".esp" or p.exists() or p.is_symlink():raise ValueError("expected new ESP")
    stages=spec["stages"];topics=spec.get("topics",[]);objectives=spec.get("objectives",[])
    if not 1<=len(stages)<=256 or len(topics)>512 or len(objectives)>256:raise ValueError("quest size limit")
    priority=spec.get("priority",50)
    if type(priority) is not int or not 0<=priority<=100:raise ValueError("invalid priority")
    next_local=0x800
    def alloc(key):
        nonlocal next_local
        if allocator is not None:return bindings.slot|allocator.get(key)
        v=next_local;next_local+=1;return bindings.slot|v
    qid=alloc("QUST/"+spec["id"].casefold());expected={qid:"QUST"};stage_ids=set();objective_ids=set()
    start_enabled=spec.get("start_enabled",False)
    if type(start_enabled) is not bool:raise ValueError("invalid start flag")
    q=sub(b"EDID",ident(spec["id"]))+sub(b"FULL",string(spec["title"],128))+sub(b"DATA",struct.pack("<BB2xf",int(start_enabled),priority,0.))
    for s in sorted(stages,key=lambda s:s["index"]):
        if set(s)-{"index","log","complete","fail","actions"}:raise ValueError("unsupported stage fields")
        n=s["index"];complete=s.get("complete",False);fail=s.get("fail",False)
        if type(n) is not int or not 0<=n<=255 or n in stage_ids or type(complete) is not bool or type(fail) is not bool or complete and fail:raise ValueError("invalid stage")
        stage_ids.add(n)
        q+=sub(b"INDX",struct.pack("<h",n))+sub(b"QSDT",bytes([1 if complete else 2 if fail else 0]))+sub(b"CNAM",string(s["log"]))+empty_script(scripts.get(f"stage_{n}",""))
    for o in sorted(objectives,key=lambda o:o["index"]):
        if set(o)-{"index","text","targets"}:raise ValueError("unsupported objective fields")
        n=o["index"]
        if type(n) is not int or not 0<=n<=2147483647 or n in objective_ids:raise ValueError("invalid objective")
        objective_ids.add(n);q+=sub(b"QOBJ",struct.pack("<i",n))+sub(b"NNAM",string(o["text"],1024))
        targets=o.get("targets",[])
        if not isinstance(targets,list) or len(targets)>64:raise ValueError("invalid objective targets")
        for target in targets:
            if set(target)-{"ref","ignore_locks","conditions"} or type(target.get("ignore_locks",False)) is not bool:raise ValueError("invalid target")
            fid=bindings.resolve(target["ref"],{"REFR","ACHR","ACRE","PGRE","PMIS"})
            q+=sub(b"QSTA",struct.pack("<IB3x",fid,int(target.get("ignore_locks",False))))+conditions(target.get("conditions",[]),qid,stage_ids,bindings)
    ids={};used={spec["id"].casefold()}
    for t in topics:
        if set(t)-{"id","prompt","responses","top_level","priority"}:raise ValueError("unsupported topic fields")
        id=t["id"]
        if not check_id(id) or id.casefold() in used:raise ValueError("duplicate topic ID")
        used.add(id.casefold());ids[id]=alloc("DIAL/"+id.casefold());expected[ids[id]]="DIAL"
    dialogue=[]
    for t in topics:
        tid=ids[t["id"]];level=t.get("top_level",False);pr=t.get("priority",50.)
        if type(level) is not bool or not math.isfinite(pr) or not 0<=pr<=100:raise ValueError("invalid topic flags")
        responses=t["responses"]
        if not 1<=len(responses)<=255:raise ValueError("response count")
        dial=sub(b"EDID",ident(t["id"]))+sub(b"QSTI",u32(qid))+sub(b"FULL",string(t["prompt"],128))+sub(b"PNAM",struct.pack("<f",pr))+sub(b"DATA",bytes([0,2 if level else 0]))
        infos=[];previous=0
        for i,r in enumerate(responses):
            if set(r)-{"text","emotion","emotion_value","goodbye","choices","notes","conditions","speaker","id","begin","end"}:raise ValueError("unsupported response fields")
            emotion=r.get("emotion",0);value=r.get("emotion_value",0);goodbye=r.get("goodbye",False);choices=r.get("choices",[])
            if type(emotion) is not int or not 0<=emotion<=7 or type(value) is not int or not 0<=value<=100 or type(goodbye) is not bool or len(choices)>64 or len(set(choices))!=len(choices) or any(c not in ids for c in choices) or goodbye and choices:raise ValueError("invalid response")
            if allocator is not None and not check_id(r.get("id")):raise ValueError("stable dialogue responses require explicit id")
            fid=alloc("INFO/"+t["id"].casefold()+"/"+str(r.get("id",i)).casefold());expected[fid]="INFO"
            info=sub(b"DATA",struct.pack("<BBH",0,0,int(goodbye)))+sub(b"QSTI",u32(qid))+sub(b"TPIC",u32(tid))+sub(b"PNAM",u32(previous))
            info+=sub(b"TRDT",struct.pack("<Ii4xB3xIB3x",emotion,value,1,0,0))+sub(b"NAM1",string(r["text"],1024))+sub(b"NAM2",string(r.get("notes",""),1024))
            info+=conditions(r.get("conditions",[]),qid,stage_ids,bindings)
            info+=b"".join(sub(b"TCLT",u32(ids[c])) for c in choices)+empty_script(scripts.get(f"{t['id']}_{i+1}_begin",""))+sub(b"NEXT",b"")+empty_script(scripts.get(f"{t['id']}_{i+1}_end",""))
            if "speaker" in r:info+=sub(b"ANAM",u32(bindings.resolve(r["speaker"],{"NPC_","CREA"})))
            infos.append(record(b"INFO",info,fid));previous=fid
        dialogue.append(record(b"DIAL",dial,tid)+group(7,tid,b"".join(infos)))
    data=group(0,b"QUST",record(b"QUST",q,qid))
    if dialogue:data=group(0,b"DIAL",b"".join(dialogue))+data
    count=len(expected)+1+(1+len(dialogue) if dialogue else 0)
    header=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,count,allocator.next if allocator else next_local))+sub(b"CNAM",b"Chimster\0")+bindings.header())
    bindings.check()
    with p.open("xb") as f:f.write(header+data)
    try:
        recs=scan(p)["records"]
        if len(recs)!=len(expected) or {bindings.slot|r["local_id"]:r["signature"] for r in recs}!=expected:raise ValueError("quest record roundtrip mismatch")
        from .world_validator import validate
        if not validate([*bindings.paths,p])["valid"]:raise ValueError("group hierarchy check failed")
        # Check references and ordering of responses independently of writer loop.
        with p.open("rb") as f:
            prev={}
            for r in recs:
                if r["signature"] not in ("INFO","DIAL"):continue
                f.seek(r["offset"]);_,n,*_=HEADER.unpack(f.read(24));parts=list(subs(f.read(n)));fields=dict(parts)
                if fields[b"QSTI"]!=u32(qid):raise ValueError("quest link mismatch")
                if r["signature"]=="INFO":
                    tid=struct.unpack("<I",fields[b"TPIC"])[0]
                    if expected.get(tid)!="DIAL" or fields[b"PNAM"]!=u32(prev.get(tid,0)):raise ValueError("topic or previous INFO mismatch")
                    prev[tid]=bindings.slot|r["local_id"]
                    if any(expected.get(struct.unpack("<I",v)[0])!="DIAL" for k,v in parts if k==b"TCLT"):raise ValueError("choice target mismatch")
        bindings.check()
    except Exception:
        p.unlink();raise
    return {"output":str(p),"quest":qid,"topics":ids,"responses":sum(v=="INFO" for v in expected.values()),"masters":[p.name for p in bindings.paths],"script_draft":bool(scripts),"uncompiled_scripts":len(scripts),"status":"UNCOMPILED DRAFT — compile in GECK before use" if scripts else "experimental structural fixture; runtime unverified"}
