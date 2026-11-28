"""Legacy compiler handoff. Native editors remain the bytecode producers."""
from pathlib import Path
import struct, hashlib, re
from .core import inspect_plugin
from .script_symbols import masked
from .compiler_diagnostics import parse as diagnostics

PROFILES={"morrowind":("TES3 Construction Set",16,8),
          "oblivion":("TES4 Construction Set",20,6),
          "fallout3":("Fallout 3 GECK",24,6),
          "newvegas":("New Vegas GECK / explicitly configured xNVSE",24,6)}
LIMIT=128*1024*1024

def lint(source,game,*,result_script=False):
    if game not in PROFILES:raise ValueError("unsupported legacy compiler profile")
    lang="morrowind" if game=="morrowind" else "oblivion" if game=="oblivion" else "geck"
    clean=masked(source,lang)
    stack=[];issues=[];names=[]
    for n,line in enumerate(clean.splitlines(),1):
        w=line.strip().split()
        if not w:continue
        first=w[0].casefold()
        if first in ("scn","scriptname") and len(w)>1:names.append(w[1])
        if first=="begin":
            if game=="morrowind" and len(w)>1:names.append(w[1])
            stack.append(("begin",n))
        elif first in ("if","while","foreach"):
            stack.append((first,n))
        elif first in ("endif","endwhile","loop","end"):
            wanted={"endif":{"if"},"endwhile":{"while"},"loop":{"while","foreach"},"end":{"begin"}}[first]
            if not stack or stack[-1][0] not in wanted:issues.append({"line":n,"message":"Unexpected "+first})
            else:stack.pop()
        elif first in ("else","elseif") and (not stack or stack[-1][0]!="if"):
            issues.append({"line":n,"message":first+" outside If"})
    for name,n in stack:issues.append({"line":n,"message":"Unclosed "+name})
    if not result_script and len(names)!=1:issues.append({"line":1,"message":"Expected one script declaration"})
    return {"game":game,"issues":issues,"script_names":names,"scope":"advisory block checks only; not a compiler"}

def fields(data,hs):
    p=0;out=[]
    while p<len(data):
        if p+hs>len(data):raise ValueError("truncated subrecord")
        sig=data[p:p+4];n=int.from_bytes(data[p+4:p+hs],"little");p+=hs
        if sig==b"XXXX":raise ValueError("extended subrecords unsupported for handoff")
        if p+n>len(data):raise ValueError("bad subrecord size")
        out.append((sig,data[p:p+n]));p+=n
    return out

def encode(parts,hs):
    return b"".join(k+len(v).to_bytes(hs-4,"little")+v for k,v in parts)

def read(path,game):
    p=Path(path)
    if game not in PROFILES or p.suffix.casefold() not in {".esp",".esm"}:raise ValueError("unsupported legacy plugin")
    if p.stat().st_size>LIMIT:raise ValueError("plugin exceeds handoff limit")
    raw=p.read_bytes()
    inspect_plugin(p,game)
    if p.read_bytes()!=raw:raise ValueError("plugin changed")
    return raw

def index(raw,game):
    _,hs,subhs=PROFILES[game]
    rows={};group_paths={}
    def walk(start,end,parents=(),labels=()):
        if len(parents)>64:raise ValueError("group depth")
        while start<end:
            if start+hs>end:raise ValueError("truncated record")
            sig=raw[start:start+4];n=struct.unpack_from("<I",raw,start+4)[0]
            stop=start+n if sig==b"GRUP" else start+hs+n
            if not start+hs<=stop<=end:raise ValueError("record boundary")
            if sig==b"GRUP":
                walk(start+hs,stop,parents+(start,),labels+(raw[start+8:start+16],))
            else:
                body=raw[start+hs:stop];header=raw[start:start+hs]
                if game=="morrowind":
                    # TES3 records lack FormIDs. Preserve exact order and all
                    # non-target records; identify SCPT by its fixed name.
                    identity=("ordinal",len(rows))
                    if sig==b"SCPT":
                        h=[v for k,v in fields(body,subhs) if k==b"SCHD"]
                        if len(h)!=1 or len(h[0])!=52:raise ValueError("bad SCHD")
                        identity=("script",h[0][:32].split(b"\0")[0].lower())
                else:identity=(sig,struct.unpack_from("<I",header,12)[0])
                if identity in rows:raise ValueError("duplicate record identity")
                rows[identity]=(start,stop,sig,header,body,parents,labels)
            start=stop
    walk(0,len(raw))
    return rows

def script_record(row,game):
    _,_,sig,header,body,_,_=row
    if sig!=b"SCPT":raise ValueError("expected standalone SCPT")
    if game!="morrowind" and struct.unpack_from("<I",header,8)[0]&0x40000:
        raise ValueError("compressed SCPT unsupported")
    parts=fields(body,PROFILES[game][2])
    def one(k):
        hits=[v for t,v in parts if t==k]
        if len(hits)!=1:raise ValueError("expected exactly one "+k.decode())
        return hits[0]
    src=one(b"SCTX")
    if game=="morrowind":
        h=one(b"SCHD");code=one(b"SCDT")
        if len(h)!=52:raise ValueError("bad SCHD")
        short,long,flt,size,local_size=struct.unpack_from("<5I",h,32)
        locals_data=[v for k,v in parts if k==b"SCVR"]
        if size!=len(code) or local_size!=sum(map(len,locals_data)):
            raise ValueError("TES3 compiled size mismatch")
        identity=h[:32]
        allowed={b"SCHD",b"SCDT",b"SCTX",b"SCVR"}
    else:
        h=one(b"SCHR");code=one(b"SCDA")
        if len(h)!=20:raise ValueError("bad SCHR")
        refs,size,variables=struct.unpack_from("<III",h,4)
        if size!=len(code) or refs!=sum(k in (b"SCRO",b"SCRV") for k,v in parts) or variables!=sum(k==b"SLSD" for k,v in parts):
            raise ValueError("compiled header count/size mismatch")
        identity=one(b"EDID")+h[16:18]
        allowed={b"SCHR",b"SCDA",b"SCTX",b"SLSD",b"SCVR",b"SCRO",b"SCRV"}
    return {"source":src,"code":code,"identity":identity,"ordinary":[(k,v) for k,v in parts if k not in allowed],"parts":parts}

def inspect(path,game):
    raw=read(path,game)
    scripts=[]
    for key,row in index(raw,game).items():
        if row[2]!=b"SCPT":continue
        try:
            s=script_record(row,game)
            scripts.append({"offset":row[0],"name":s["identity"].split(b"\0")[0].decode("cp1252",errors="replace"),
                            "source_sha256":hashlib.sha256(s["source"]).hexdigest(),"compiled_bytes":len(s["code"])})
        except ValueError as exc:scripts.append({"offset":row[0],"unsupported":str(exc)})
    return {"game":game,"editor":PROFILES[game][0],"plugin_sha256":hashlib.sha256(raw).hexdigest(),
            "scripts":scripts,"scope":"standalone SCPT structural inspection; no opcode validation"}

def attach(draft,donor,output,game):
    p,d,q=map(Path,(draft,donor,output))
    if len({p.resolve(),d.resolve(),q.resolve()})!=3 or p.name!=d.name or p.name!=q.name or q.exists() or q.is_symlink():
        raise ValueError("three distinct same-name plugin paths required")
    raw=read(p,game);compiled=read(d,game)
    a,b=index(raw,game),index(compiled,game)
    if list(a)!=list(b):raise ValueError("record identity/order changed")
    changes={};hs=PROFILES[game][1]
    for key,row in a.items():
        other=b[key]
        start,stop,sig,h,body,parents,labels=row
        if labels!=other[6] or h[:4]!=other[3][:4] or h[8:]!=other[3][8:]:
            raise ValueError("record header or group ownership changed")
        if body==other[4]:continue
        if sig!=b"SCPT":raise ValueError("non-script record changed")
        old,new=script_record(row,game),script_record(other,game)
        normalized=lambda s:s.rstrip(b"\0").replace(b"\r\n",b"\n")
        if old["identity"]!=new["identity"] or old["ordinary"]!=new["ordinary"] or normalized(old["source"])!=normalized(new["source"]):
            raise ValueError("script identity, source or unrelated data changed")
        if not new["code"]:raise ValueError("donor script has no compiled bytecode")
        changes[start]=other[4]
    if not changes:raise ValueError("no changed compiled scripts")
    result=bytearray(raw)
    # Reverse-order replacements preserve offsets of all earlier records.
    offsets={v[0]:v for v in a.values()}
    for start in sorted(changes,reverse=True):
        row=offsets[start]
        payload=changes[start];delta=len(payload)-len(row[4])
        result[start+hs:row[1]]=payload
        struct.pack_into("<I",result,start+4,len(payload))
        for g in row[5]:
            struct.pack_into("<I",result,g+4,struct.unpack_from("<I",result,g+4)[0]+delta)
    if p.read_bytes()!=raw or d.read_bytes()!=compiled:raise ValueError("input changed")
    with q.open("xb") as stream:stream.write(result)
    try:
        final=read(q,game);idx=index(final,game)
        if list(idx)!=list(a):raise ValueError("output identity mismatch")
        for key,row in a.items():
            if idx[key][4]!=changes.get(row[0],row[4]):raise ValueError("output payload mismatch")
    except Exception:q.unlink();raise
    return {"output":str(q),"attached_scripts":len(changes),"scope":"editor-compiled donor transport; no opcode or engine certification"}

def prepare(draft,output,game,identity,source_path):
    """Replace one existing standalone script's source and invalidate its bytecode.
    The result is an editor compilation draft, NOT a playable plugin.
    """
    p,q=map(Path,(draft,output))
    if p.resolve()==q.resolve() or p.name!=q.name or q.exists() or q.is_symlink():
        raise ValueError("new same-name plugin in separate directory required")
    source_path=Path(source_path)
    if source_path.stat().st_size>512*1024:raise ValueError("source too large")
    source=source_path.read_text(encoding="utf-8-sig")
    checked=lint(source,game)
    if len(checked["script_names"])!=1:raise ValueError("one named script required")
    try:encoded=source.replace("\r\n","\n").replace("\n","\r\n").encode("cp1252")
    except UnicodeEncodeError as exc:raise ValueError("source requires an unsupported legacy encoding") from exc
    if b"\0" in encoded:raise ValueError("NUL in script source")
    raw=read(p,game);rows=index(raw,game);hs,subhs=PROFILES[game][1:]
    matches=[]
    for key,row in rows.items():
        if row[2]!=b"SCPT":continue
        if game=="morrowind":
            if key[1].decode("cp1252").casefold()!=str(identity).casefold():continue
        else:
            if key[1]!=int(str(identity),0):continue
        matches.append(row)
    if len(matches)!=1:raise ValueError("missing or ambiguous script identity")
    row=matches[0];old=script_record(row,game)
    name=old["identity"].split(b"\0")[0].decode("cp1252")
    if name.casefold()!=checked["script_names"][0].casefold():raise ValueError("source declaration differs from record name")
    header_tag,code_tag=(b"SCHD",b"SCDT") if game=="morrowind" else (b"SCHR",b"SCDA")
    parts=[]
    for k,v in old["parts"]:
        if k==header_tag:
            v=v[:32]+bytes(20) if game=="morrowind" else v[:4]+bytes(12)+v[16:]
        elif k==code_tag:v=b""
        elif k==b"SCTX":v=encoded+(b"\0" if v.endswith(b"\0") else b"")
        elif k in {b"SCVR",b"SLSD",b"SCRO",b"SCRV"}:continue
        parts.append((k,v))
    body=encode(parts,subhs);start,stop=row[:2]
    result=bytearray(raw[:start+hs]+body+raw[stop:])
    delta=len(body)-len(row[4])
    struct.pack_into("<I",result,start+4,len(body))
    for g in row[5]:struct.pack_into("<I",result,g+4,struct.unpack_from("<I",result,g+4)[0]+delta)
    if p.read_bytes()!=raw:raise ValueError("source plugin changed")
    with q.open("xb") as f:f.write(result)
    try:
        rebuilt=index(read(q,game),game)
        if list(rebuilt)!=list(rows):raise ValueError("draft identity mismatch")
        for key,original in rows.items():
            if rebuilt[key][4]!=(body if original[0]==start else original[4]):raise ValueError("draft payload mismatch")
    except Exception:q.unlink();raise
    return {"output":str(q),"script":name,"diagnostics":checked["issues"],"status":"uncompiled-draft",
            "scope":"compile and save this copy using the native editor before any game use"}
