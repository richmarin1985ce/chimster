"""Experimental FNV quest and dialogue record fixture writer.
Optional verified dependencies; no compiled scripts or engine certification."""
from pathlib import Path
import struct,math
from .fnv_patch import sub,record
from .fnv_world import group,cstr
from .fnv_content import ident
from .fnv_records import scan,HEADER,subs
from .quest_editor import check_id
from .record_schema import integer,number

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
    if set(spec)-{"schema","id","title","priority","stages","objectives","topics","start_enabled","repeat_topics","repeat_stages","delay","conditions","quest_script"}:raise ValueError("unsupported native quest fields")
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
    if any(type(spec.get(k,False)) is not bool for k in ("repeat_topics","repeat_stages")):raise ValueError("invalid repeat flags")
    flags=int(start_enabled)+4*int(spec.get("repeat_topics",False))+8*int(spec.get("repeat_stages",False))
    all_stages={s["index"] for s in stages}
    q=sub(b"EDID",ident(spec["id"]))
    if "quest_script" in spec:q+=sub(b"SCRI",u32(bindings.resolve(spec["quest_script"],{"SCPT"})))
    q+=sub(b"FULL",string(spec["title"],128))+sub(b"DATA",struct.pack("<BB2xf",flags,priority,number(spec.get("delay",0),0,3600)))+conditions(spec.get("conditions",[]),qid,all_stages,bindings)
    for s in sorted(stages,key=lambda s:s["index"]):
        if set(s)-{"index","log","complete","fail","actions","conditions","next_quest"}:raise ValueError("unsupported stage fields")
        n=s["index"];complete=s.get("complete",False);fail=s.get("fail",False)
        if type(n) is not int or not 0<=n<=255 or n in stage_ids or type(complete) is not bool or type(fail) is not bool or complete and fail:raise ValueError("invalid stage")
        stage_ids.add(n)
        q+=sub(b"INDX",struct.pack("<h",n))+sub(b"QSDT",bytes([1 if complete else 2 if fail else 0]))+conditions(s.get("conditions",[]),qid,all_stages,bindings)+sub(b"CNAM",string(s["log"]))+empty_script(scripts.get(f"stage_{n}",""))
        if "next_quest" in s:q+=sub(b"NAM0",u32(bindings.resolve(s["next_quest"],{"QUST"})))
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
        if set(t)-{"id","prompt","responses","top_level","priority","type","rumors"}:raise ValueError("unsupported topic fields")
        id=t["id"]
        if not check_id(id) or id.casefold() in used:raise ValueError("duplicate topic ID")
        used.add(id.casefold());ids[id]=alloc("DIAL/"+id.casefold());expected[ids[id]]="DIAL"
    dialogue=[]
    for t in topics:
        tid=ids[t["id"]];level=t.get("top_level",False);pr=t.get("priority",50.)
        if type(level) is not bool or not math.isfinite(pr) or not 0<=pr<=100:raise ValueError("invalid topic flags")
        responses=t["responses"]
        if not 1<=len(responses)<=255:raise ValueError("response count")
        typ=integer(t.get("type",0),0,7);rumors=t.get("rumors",False)
        if type(rumors) is not bool:raise ValueError("invalid rumor flag")
        dial=sub(b"EDID",ident(t["id"]))+sub(b"QSTI",u32(qid))+sub(b"FULL",string(t["prompt"],128))+sub(b"PNAM",struct.pack("<f",pr))+sub(b"DATA",bytes([typ,2*int(level)+int(rumors)]))
        infos=[];previous=0
        for i,r in enumerate(responses):
            if set(r)-{"text","emotion","emotion_value","goodbye","choices","notes","conditions","speaker","id","begin","end","lines","flags","next_speaker","prompt","speech_challenge","challenge_actor_value","link_from"}:raise ValueError("unsupported response fields")
            emotion=r.get("emotion",0);value=r.get("emotion_value",0);goodbye=r.get("goodbye",False);choices=r.get("choices",[])
            if type(emotion) is not int or not 0<=emotion<=7 or type(value) is not int or not 0<=value<=100 or type(goodbye) is not bool or len(choices)>64 or len(set(choices))!=len(choices) or any(c not in ids for c in choices) or goodbye and choices:raise ValueError("invalid response")
            if allocator is not None and not check_id(r.get("id")):raise ValueError("stable dialogue responses require explicit id")
            fid=alloc("INFO/"+t["id"].casefold()+"/"+str(r.get("id",i)).casefold());expected[fid]="INFO"
            flag_names={"random":2,"say_once":4,"run_immediately":8,"refusal":16,"random_end":32,"run_for_rumors":64,"speech_challenge":128,"say_once_daily":256,"always_darken":512,"low_intelligence":4096,"high_intelligence":8192}
            flags=r.get("flags",[])
            if not isinstance(flags,list) or len(set(flags))!=len(flags) or any(f not in flag_names for f in flags):raise ValueError("invalid INFO flags")
            if ("speech_challenge" in flags)!=("speech_challenge" in r) or "challenge_actor_value" in r and "speech_challenge" not in flags:raise ValueError("speech challenge flag and data must match")
            info=sub(b"DATA",struct.pack("<BBH",typ,integer(r.get("next_speaker",0),0,2),int(goodbye)+sum(flag_names[f] for f in flags)))+sub(b"QSTI",u32(qid))+sub(b"TPIC",u32(tid))+sub(b"PNAM",u32(previous))
            if "lines" in r and "text" in r:raise ValueError("choose text or response lines")
            lines=r.get("lines",[{"text":r.get("text"),"emotion":emotion,"emotion_value":value,"notes":r.get("notes","")}])
            if not isinstance(lines,list) or not 1<=len(lines)<=255:raise ValueError("invalid response lines")
            for j,line in enumerate(lines,1):
                if set(line)-{"text","emotion","emotion_value","notes","sound","emotion_animation","speaker_animation","listener_animation"}:raise ValueError("unsupported response line")
                anim=line.get("emotion_animation",False)
                if type(anim) is not bool:raise ValueError("invalid emotion animation flag")
                info+=sub(b"TRDT",struct.pack("<Ii4xB3xIB3x",integer(line.get("emotion",0),0,7),integer(line.get("emotion_value",0),0,100),j,bindings.resolve(line["sound"],{"SOUN"}) if "sound" in line else 0,int(anim)))+sub(b"NAM1",string(line["text"],1024))+sub(b"NAM2",string(line.get("notes",""),1024))
                for field,tag in (("speaker_animation",b"SNAM"),("listener_animation",b"LNAM")):
                    if field in line:info+=sub(tag,u32(bindings.resolve(line[field],{"IDLE"})))
            info+=conditions(r.get("conditions",[]),qid,stage_ids,bindings)
            links=r.get("link_from",[])
            if not isinstance(links,list) or len(links)>64 or len(set(links))!=len(links) or any(c not in ids for c in links):raise ValueError("invalid linked topic")
            info+=b"".join(sub(b"TCLT",u32(ids[c])) for c in choices)+b"".join(sub(b"TCLF",u32(ids[c])) for c in links)+empty_script(scripts.get(f"{t['id']}_{i+1}_begin",""))+sub(b"NEXT",b"")+empty_script(scripts.get(f"{t['id']}_{i+1}_end",""))
            if "prompt" in r:info+=sub(b"RNAM",string(r["prompt"],128))
            if "speaker" in r:info+=sub(b"ANAM",u32(bindings.resolve(r["speaker"],{"NPC_","CREA"})))
            if "challenge_actor_value" in r:info+=sub(b"KNAM",u32(bindings.resolve(r["challenge_actor_value"],{"AVIF","PERK"})))
            if "speech_challenge" in r:info+=sub(b"DNAM",u32(integer(r["speech_challenge"],1,5)))
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
