"""Experimental masterless FNV quest and dialogue record fixture writer.
No runtime quest wiring, NPC assignment, or compiled scripts."""
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
def empty_script():
    return sub(b"SCHR",bytes(20))+sub(b"SCDA",b"")+sub(b"SCTX",b"")
def export(spec,output):
    if spec.get("schema")!=1 or not check_id(spec.get("id")):raise ValueError("invalid native quest specification")
    if set(spec)-{"schema","id","title","priority","stages","objectives","topics"}:raise ValueError("unsupported native quest fields")
    p=Path(output)
    if p.suffix.lower()!=".esp" or p.exists() or p.is_symlink():raise ValueError("expected new ESP")
    stages=spec["stages"];topics=spec.get("topics",[]);objectives=spec.get("objectives",[])
    if not 1<=len(stages)<=256 or len(topics)>512 or len(objectives)>256:raise ValueError("quest size limit")
    priority=spec.get("priority",50)
    if type(priority) is not int or not 0<=priority<=100:raise ValueError("invalid priority")
    qid=0x800;next_id=qid+1;expected={qid:"QUST"};stage_ids=set();objective_ids=set()
    q=sub(b"EDID",ident(spec["id"]))+sub(b"FULL",string(spec["title"],128))+sub(b"DATA",struct.pack("<BB2xf",0,priority,0.))
    for s in sorted(stages,key=lambda s:s["index"]):
        if set(s)-{"index","log","complete","fail"}:raise ValueError("unsupported stage fields")
        n=s["index"];complete=s.get("complete",False);fail=s.get("fail",False)
        if type(n) is not int or not 0<=n<=255 or n in stage_ids or type(complete) is not bool or type(fail) is not bool or complete and fail:raise ValueError("invalid stage")
        stage_ids.add(n)
        q+=sub(b"INDX",struct.pack("<h",n))+sub(b"QSDT",bytes([1 if complete else 2 if fail else 0]))+sub(b"CNAM",string(s["log"]))+empty_script()
    for o in sorted(objectives,key=lambda o:o["index"]):
        if set(o)!={"index","text"}:raise ValueError("unsupported objective fields")
        n=o["index"]
        if type(n) is not int or not 0<=n<=2147483647 or n in objective_ids:raise ValueError("invalid objective")
        objective_ids.add(n);q+=sub(b"QOBJ",struct.pack("<i",n))+sub(b"NNAM",string(o["text"],1024))
    ids={};used={spec["id"].casefold()}
    for t in topics:
        if set(t)-{"id","prompt","responses","top_level","priority"}:raise ValueError("unsupported topic fields")
        id=t["id"]
        if not check_id(id) or id.casefold() in used:raise ValueError("duplicate topic ID")
        used.add(id.casefold());ids[id]=next_id;expected[next_id]="DIAL";next_id+=1
    dialogue=[]
    for t in topics:
        tid=ids[t["id"]];level=t.get("top_level",False);pr=t.get("priority",50.)
        if type(level) is not bool or not math.isfinite(pr) or not 0<=pr<=100:raise ValueError("invalid topic flags")
        responses=t["responses"]
        if not 1<=len(responses)<=255:raise ValueError("response count")
        dial=sub(b"EDID",ident(t["id"]))+sub(b"QSTI",u32(qid))+sub(b"FULL",string(t["prompt"],128))+sub(b"PNAM",struct.pack("<f",pr))+sub(b"DATA",bytes([0,2 if level else 0]))
        infos=[];previous=0
        for r in responses:
            if set(r)-{"text","emotion","emotion_value","goodbye","choices","notes"}:raise ValueError("unsupported response fields")
            emotion=r.get("emotion",0);value=r.get("emotion_value",0);goodbye=r.get("goodbye",False);choices=r.get("choices",[])
            if type(emotion) is not int or not 0<=emotion<=7 or type(value) is not int or not 0<=value<=100 or type(goodbye) is not bool or len(choices)>64 or len(set(choices))!=len(choices) or any(c not in ids for c in choices) or goodbye and choices:raise ValueError("invalid response")
            fid=next_id;next_id+=1;expected[fid]="INFO"
            info=sub(b"DATA",struct.pack("<BBH",0,0,int(goodbye)))+sub(b"QSTI",u32(qid))+sub(b"TPIC",u32(tid))+sub(b"PNAM",u32(previous))
            info+=sub(b"TRDT",struct.pack("<Ii4xB3xIB3x",emotion,value,1,0,0))+sub(b"NAM1",string(r["text"],1024))+sub(b"NAM2",string(r.get("notes",""),1024))
            info+=b"".join(sub(b"TCLT",u32(ids[c])) for c in choices)+empty_script()+sub(b"NEXT",b"")+empty_script()
            infos.append(record(b"INFO",info,fid));previous=fid
        dialogue.append(record(b"DIAL",dial,tid)+group(7,tid,b"".join(infos)))
    data=group(0,b"QUST",record(b"QUST",q,qid))
    if dialogue:data=group(0,b"DIAL",b"".join(dialogue))+data
    count=len(expected)+1+(1+len(dialogue) if dialogue else 0)
    header=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,count,next_id))+sub(b"CNAM",b"Chimster\0"))
    with p.open("xb") as f:f.write(header+data)
    try:
        recs=scan(p)["records"]
        if len(recs)!=len(expected) or {r["local_id"]:r["signature"] for r in recs}!=expected:raise ValueError("quest record roundtrip mismatch")
        from .world_validator import validate
        if not validate([p])["valid"]:raise ValueError("group hierarchy check failed")
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
                    prev[tid]=r["local_id"]
                    if any(expected.get(struct.unpack("<I",v)[0])!="DIAL" for k,v in parts if k==b"TCLT"):raise ValueError("choice target mismatch")
    except Exception:
        p.unlink();raise
    return {"output":str(p),"quest":qid,"topics":ids,"responses":sum(v=="INFO" for v in expected.values()),"status":"experimental structural fixture; scripts, speaker conditions and runtime wiring not generated"}
