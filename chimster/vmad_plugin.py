"""Staged existing VMAD edits in Skyrim-family plugins, no record remapping."""
from pathlib import Path
import struct
import hashlib
from .vmad import parse, edit, GAMES, MAX
from .core import inspect_plugin

LIMIT=128*1024*1024
# Deliberately restricted to records with plain script tables, no fragments.
EDITABLE={b"ACTI",b"CONT",b"DOOR",b"MISC",b"NPC_",b"REFR",b"ACHR",b"FLOR",b"FURN"}

def load(path,game):
    p=Path(path)
    if game not in GAMES or p.suffix.lower() not in {".esp",".esm",".esl"}:
        raise ValueError("expected Skyrim-family plugin")
    if p.stat().st_size>LIMIT:raise ValueError("plugin size limit")
    raw=p.read_bytes()
    inspect_plugin(p,"skyrimse" if game=="skyrimae" else game)
    if p.read_bytes()!=raw:raise ValueError("plugin changed during inspection")
    return raw

def locate(raw,form):
    found=[]
    def walk(a,b,groups=()):
        if len(groups)>64:raise ValueError("group nesting limit")
        while a<b:
            if a+24>b:raise ValueError("truncated header")
            sig,n,flags,fid=struct.unpack_from("<4sIII",raw,a)
            end=a+n if sig==b"GRUP" else a+24+n
            if end<a+24 or end>b:raise ValueError("invalid record boundary")
            if sig==b"GRUP":walk(a+24,end,groups+(a,))
            elif fid==form and sig!=b"TES4":found.append((a,end,sig,flags,groups))
            a=end
    if type(form) is not int or not 0<form<=0xffffffff:raise ValueError("expected nonzero disk FormID")
    walk(0,len(raw))
    if len(found)!=1:raise ValueError("missing or duplicate disk FormID")
    a,end,sig,flags,groups=found[0]
    if flags&0x40000:raise ValueError("compressed target not supported")
    start=a+24
    fields=[]
    while start<end:
        if start+6>end:raise ValueError("truncated subrecord")
        k,n=struct.unpack_from("<4sH",raw,start)
        header=start
        start+=6
        if k==b"XXXX":
            if n!=4 or start+10>end:raise ValueError("invalid XXXX")
            n=struct.unpack_from("<I",raw,start)[0]
            k,_=struct.unpack_from("<4sH",raw,start+4)
            if k==b"XXXX":raise ValueError("nested XXXX")
            start+=10
        if start+n>end:raise ValueError("invalid subrecord")
        if k==b"VMAD":fields.append((header,start,start+n))
        start+=n
    if len(fields)!=1:raise ValueError("expected one existing VMAD")
    return a,end,sig,groups,fields[0]

def inspect(path,game,form):
    raw=load(path,game)
    a,end,sig,groups,(_,start,stop)=locate(raw,form)
    return {"plugin_sha256":hashlib.sha256(raw).hexdigest(),"disk_form_id":form,
            "signature":sig.decode("ascii"),**parse(raw[start:stop],game)}

def stage(path,output,game,form,script,prop,value,expected_plugin_sha256,expected_vmad_sha256):
    p=Path(path);q=Path(output)
    if p.name!=q.name or p.resolve()==q.resolve() or q.exists() or q.is_symlink():
        raise ValueError("new same-name plugin in a separate staging directory required")
    raw=load(p,game)
    if hashlib.sha256(raw).hexdigest()!=expected_plugin_sha256:raise ValueError("stale plugin snapshot")
    a,end,sig,groups,(header,start,stop)=locate(raw,form)
    if sig not in EDITABLE:raise ValueError("record family not enabled for VMAD edits")
    data=edit(raw[start:stop],game,script,prop,value,expected_vmad_sha256)
    if len(data)>MAX:raise ValueError("edited VMAD too large")
    # Preserve all other subrecords, flags, group labels, and record identities.
    sub=b"VMAD"+struct.pack("<H",len(data))+data if len(data)<=65535 else (
        b"XXXX\x04\x00"+struct.pack("<I",len(data))+b"VMAD\x00\x00"+data)
    delta=len(sub)-(stop-header)
    out=bytearray(raw[:header]+sub+raw[stop:])
    for offset in (*groups,a):
        old=struct.unpack_from("<I",raw,offset+4)[0]
        struct.pack_into("<I",out,offset+4,old+delta)
    if p.read_bytes()!=raw:raise ValueError("source changed")
    with q.open("xb") as stream:stream.write(out)
    try:
        result=inspect(q,game,form)
        if result["sha256"]!=hashlib.sha256(data).hexdigest():raise ValueError("output VMAD mismatch")
    except Exception:
        q.unlink();raise
    return {"output":str(q),**result}
