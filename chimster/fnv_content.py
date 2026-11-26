"""Narrow masterless FNV record constructors, original MIT code."""
import math,struct,re
from pathlib import Path
from .fnv_patch import sub,record
from .fnv_world import cstr,group
from .fnv_records import scan,subs,HEADER

def ident(s):
    if not isinstance(s,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}",s):raise ValueError("invalid editor ID")
    return cstr(s)
def asset(s,ext):
    if not isinstance(s,str):raise ValueError("expected relative asset path")
    p=s.replace("\\","/").split("/")
    if any(not re.fullmatch(r"[A-Za-z0-9_. -]+",x) or x in (".","..") for x in p) or not p[-1].lower().endswith(ext):raise ValueError("unsafe asset path")
    return cstr("\\".join(p))
def bounds(b):
    if len(b)!=6 or any(not isinstance(x,int) or not -32768<=x<=32767 for x in b) or any(b[i]>b[i+3] for i in range(3)):raise ValueError("invalid object bounds")
    return sub(b"OBND",struct.pack("<6h",*b))
def static(form,s):
    return record(b"STAT",sub(b"EDID",ident(s["id"]))+bounds(s["bounds"])+sub(b"MODL",asset(s["model"],".nif")),form)
def reference(form,base,x,y,z,yaw=0.,scale=1.):
    if not all(math.isfinite(v) and abs(v)<=1e7 for v in (x,y,z,yaw,scale)) or not .01<=scale<=10:raise ValueError("invalid reference transform")
    return record(b"REFR",sub(b"NAME",struct.pack("<I",base))+sub(b"XSCL",struct.pack("<f",scale))+sub(b"DATA",struct.pack("<6f",x,y,z,0,0,math.radians(yaw))),form)
def textures(tx,lt,s):
    a=record(b"TXST",sub(b"EDID",ident(s["id"]+"TX"))+bounds([0]*6)+sub(b"TX00",asset(s["diffuse"],".dds"))+sub(b"TX01",asset(s["normal"],".dds"))+sub(b"DNAM",bytes(2)),tx)
    material=s.get("material",2)
    if not isinstance(material,int) or not 0<=material<=30:raise ValueError("invalid material")
    b=record(b"LTEX",sub(b"EDID",ident(s["id"]))+sub(b"ICON",b"\0")+sub(b"MICO",b"\0")+sub(b"TNAM",struct.pack("<I",tx))+sub(b"HNAM",bytes((material,30,0)))+sub(b"SNAM",b"\x1e"),lt)
    return a,b
def book_record(form,b,model=None,value=1,weight=.2,object_bounds=(0,0,0,8,8,2),skill=-1,untakeable=False):
    b.validate()
    if b.game!="newvegas":raise ValueError("native writer is New Vegas only")
    content=(b.author+"\n\n" if b.author else "")+"\n\n".join(b.pages)
    body=sub(b"EDID",ident(b.editor_id))+bounds(object_bounds)+sub(b"FULL",cstr(b.title))
    if model:body+=sub(b"MODL",asset(model,".nif"))
    if type(skill) is not int or skill not in {-1,0,2,3,4,5,6,7,8,9,10,11,12,13} or type(untakeable) is not bool:raise ValueError("invalid book skill/flags")
    if b.kind!="book" and (skill!=-1 or untakeable):raise ValueError("skill and book flags require BOOK")
    if b.kind=="book":
        if not model:raise ValueError("BOOK requires author-supplied model path")
        if not isinstance(value,int) or not 0<=value<=2**31-1 or not math.isfinite(weight) or not 0<=weight<=1000:raise ValueError("invalid book value/weight")
        return b"BOOK",record(b"BOOK",body+sub(b"DESC",cstr(content))+sub(b"DATA",struct.pack("<Bbif",2 if untakeable else 0,skill,value,weight)),form)
    return b"NOTE",record(b"NOTE",body+sub(b"DATA",b"\x01")+sub(b"TNAM",cstr(content)),form)
def export_book(b,output,model=None,skill=-1,untakeable=False):
    sig,raw=book_record(0x800,b,model,skill=skill,untakeable=untakeable)
    p=Path(output)
    if p.suffix.lower()!=".esp" or p.exists() or p.is_symlink():raise ValueError("expected new ESP")
    header=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,2,0x801))+sub(b"CNAM",b"Chimster\0"))
    with p.open("xb") as f:f.write(header+group(0,sig,raw))
    try:
        r=scan(p)["records"]
        if len(r)!=1 or r[0]["signature"]!=sig.decode() or r[0]["local_id"]!=0x800:raise ValueError("book roundtrip mismatch")
        with p.open("rb") as f:
            f.seek(r[0]["offset"]);_,size,*_=HEADER.unpack(f.read(24));fields=dict(subs(f.read(size)))
        if fields[b"FULL"]!=cstr(b.title) or fields[b"DESC" if sig==b"BOOK" else b"TNAM"]!=cstr((b.author+"\n\n" if b.author else "")+"\n\n".join(b.pages)):raise ValueError("text mismatch")
    except Exception:
        p.unlink();raise
    return {"output":str(p),"signature":sig.decode(),"form_id":2048,"status":"self-reader verified; engine validation pending"}
