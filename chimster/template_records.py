"""Clone explicit locally supplied native templates without guessing opaque FormIDs.

The source file's complete slot table must be a prefix of the destination masters.
All retained embedded FormIDs therefore retain their original meaning. Self-references
continue to refer to the original template; this is not a general semantic clone.
"""
import struct,zlib
from .fnv_records import scan,subs,HEADER,MAX_RECORD
from .fnv_world import cstr
from .fnv_content import ident
from .fnv_patch import sub
from .loadorder import plugin_name
from .record_schema import integer,number
from .gameplay_records import inventory,rows,check,u32
KINDS={"NPC_","RACE","WEAP","ARMO","PACK","MGEF"}
def clone(sig,id,fields,bindings,link):
    allowed={"template","title"}
    if sig=="NPC_":allowed|={"health","special","level","factions","items","packages","race","voice","class"}
    if sig=="WEAP":allowed|={"value","health","weight","damage","clip_size"}
    if sig=="ARMO":allowed|={"value","health","weight","damage_threshold"}
    if sig=="PACK":allowed={"template"}
    if sig=="MGEF":allowed|={"description"}
    check(fields,{"template"},allowed-{"template"})
    t=fields["template"];check(t,{"plugin","id"})
    origin=plugin_name(t["plugin"]);local=integer(t["id"],1,0xffffff)
    if origin not in bindings.names:raise ValueError("template must be an explicit dependency")
    path=bindings.paths[bindings.names.index(origin)];report=scan(path)
    slots=[plugin_name(m) for m in report["masters"]]+[origin]
    if bindings.names[:len(slots)]!=slots:raise ValueError("opaque template requires identical master slot prefix")
    matches=[r for r in report["records"] if r["origin"]==origin and r["local_id"]==local and r["signature"]==sig]
    if len(matches)!=1:raise ValueError("template must be a unique record owned by its source file")
    r=matches[0]
    if r["flags"]&~0x40000:raise ValueError("special/deleted template flags unsupported")
    with path.open("rb") as f:
        f.seek(r["offset"]);_,n,flags,*_=HEADER.unpack(f.read(24));data=f.read(n)
    import hashlib
    if hashlib.sha256(data).hexdigest()!=r["payload_sha256"]:raise ValueError("template changed")
    if flags&0x40000:
        if len(data)<4:raise ValueError("short compressed template")
        n=struct.unpack_from("<I",data)[0]
        if n>MAX_RECORD:raise ValueError("template too large")
        d=zlib.decompressobj();data=d.decompress(data[4:],n+1)
        if len(data)!=n or not d.eof or d.unused_data or d.unconsumed_tail:raise ValueError("invalid compressed template")
    parts=list(subs(data))
    def one(tag):
        found=[v for k,v in parts if k==tag]
        if len(found)!=1:raise ValueError("template requires unique "+tag.decode())
        return found[0]
    replacements={b"EDID":ident(id)}
    one(b"EDID")
    if "title" in fields:one(b"FULL");replacements[b"FULL"]=cstr(fields["title"])
    if "description" in fields:one(b"DESC");replacements[b"DESC"]=cstr(fields["description"])
    collections={}
    if sig=="NPC_":
        acbs=bytearray(one(b"ACBS"))
        if len(acbs)!=24:raise ValueError("unsupported NPC ACBS")
        flags=struct.unpack_from("<I",acbs)[0]
        if flags&0x100 or any(k==b"TPLT" and v!=bytes(4) for k,v in parts):raise ValueError("template-inheriting NPCs need explicit flattening")
        if "level" in fields:
            if flags&0x80:raise ValueError("PC-level-mult template requires explicit conversion")
            struct.pack_into("<h",acbs,8,integer(fields["level"],1,32767));replacements[b"ACBS"]=bytes(acbs)
        if "health" in fields or "special" in fields:
            stats=bytearray(one(b"DATA"))
            if len(stats)<11:raise ValueError("unsupported NPC DATA")
            if "health" in fields:struct.pack_into("<i",stats,0,integer(fields["health"],1,2**31-1))
            if "special" in fields:
                vals=fields["special"]
                if not isinstance(vals,list) or len(vals)!=7:raise ValueError("expected seven SPECIAL values")
                stats[4:11]=bytes(integer(v,1,10) for v in vals)
            replacements[b"DATA"]=bytes(stats)
        for key,tag,kinds in (("race",b"RNAM",{"RACE"}),("voice",b"VTCK",{"VTYP"}),("class",b"CNAM",{"CLAS"})):
            if key in fields:one(tag);replacements[tag]=u32(link(fields[key],kinds))
        if "factions" in fields:
            out=[];seen=set()
            for v in rows(fields["factions"]):
                check(v,{"ref","rank"});fid=link(v["ref"],{"FACT"})
                if fid in seen:raise ValueError("duplicate faction")
                seen.add(fid);out.append((b"SNAM",struct.pack("<IB3x",fid,integer(v["rank"],0,127))))
            collections[b"SNAM"]=(out,b"INAM" if any(k==b"INAM" for k,v in parts) else b"VTCK")
        if "items" in fields:
            collections[b"CNTO"]=(list(subs(inventory(fields["items"],link))),next((k for k,v in parts if k in (b"AIDT",b"PKID",b"CNAM")),b"CNAM"))
            if any(k==b"COED" for k,v in parts):raise ValueError("template has item ownership/condition data; explicit handling required")
        if "packages" in fields:
            collections[b"PKID"]=([(b"PKID",u32(link(v,{"PACK"}))) for v in rows(fields["packages"])],b"CNAM")
    if sig in {"WEAP","ARMO"}:
        stats=bytearray(one(b"DATA"));expected=15 if sig=="WEAP" else 12
        if len(stats)!=expected:raise ValueError("unsupported equipment DATA")
        for key,fmt,off,lo,hi in (("value","i",0,0,2**31-1),("health","i",4,1,2**31-1),("weight","f",8,0,1000)):
            if key in fields:struct.pack_into("<"+fmt,stats,off,number(fields[key],lo,hi) if fmt=="f" else integer(fields[key],lo,hi))
        if sig=="WEAP":
            if "damage" in fields:struct.pack_into("<h",stats,12,integer(fields["damage"],0,32767))
            if "clip_size" in fields:struct.pack_into("<B",stats,14,integer(fields["clip_size"],0,255))
        replacements[b"DATA"]=bytes(stats)
        if "damage_threshold" in fields:
            d=bytearray(one(b"DNAM"))
            if len(d)!=12:raise ValueError("unsupported armor DNAM")
            struct.pack_into("<f",d,4,number(fields["damage_threshold"],0,1000));replacements[b"DNAM"]=bytes(d)
    # Preserve exact untouched subrecord bytes, including extended headers.
    pos=0;output=[];done=set();present={k for k,v in parts}
    while pos<len(data):
        start=pos;tag,n=struct.unpack_from("<4sH",data,pos);pos+=6
        if tag==b"XXXX":
            n=struct.unpack_from("<I",data,pos)[0];pos+=4;tag,_=struct.unpack_from("<4sH",data,pos);pos+=6
        pos+=n
        for coll,(new,anchor) in collections.items():
            if coll not in present and tag==anchor and coll not in done:
                output.extend(sub(k,v) for k,v in new);done.add(coll)
        if tag in collections:
            if tag not in done:output.extend(sub(k,v) for k,v in collections[tag][0]);done.add(tag)
        elif tag in replacements:output.append(sub(tag,replacements[tag]))
        else:output.append(data[start:pos])
    if any(k not in done for k in collections):raise ValueError("missing collection insertion anchor")
    return b"".join(output)
