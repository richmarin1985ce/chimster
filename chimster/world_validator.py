"""Read-only Fallout New Vegas worldspace hierarchy and merged-load-order validator."""
from pathlib import Path
from collections import Counter
import struct,zlib,math
from .fnv_records import HEADER,MAX_RECORD,subs,text
from .loadorder import plugin_name

TOP="GMST TXST MICN GLOB CLAS FACT HDPT HAIR EYES RACE SOUN ASPC MGEF SCPT LTEX ENCH SPEL ACTI TACT TERM ARMO BOOK CONT DOOR INGR LIGH MISC STAT SCOL MSTT PWAT GRAS TREE FURN WEAP AMMO NPC_ CREA LVLC LVLN KEYM ALCH IDLM NOTE COBJ PROJ LVLI WTHR CLMT REGN NAVI DIAL QUST IDLE PACK CSTY LSCR ANIO WATR EFSH EXPL DEBR IMGS IMAD FLST PERK BPTD ADDN AVIF RADS CAMS CPTH VTYP IPCT IPDS ARMA ECZN MESG RGDL DOBJ LGTM MUSC IMOD REPU RCPE RCCT CHIP CSNO LSCT MSET ALOC CHAL AMEF CCRD CMNY CDCK DEHY HUNG SLPD CELL WRLD".split()
REFS={"REFR","ACHR","ACRE","PGRE","PMIS"}
KINDS=REFS|{"WRLD","CELL","LAND","NAVM","ROAD","LTEX"}
DELETED=0x20
PERSISTENT=0x400

def validate(paths,max_records=2000000,max_issues=10000,quest_links=False):
    paths=[Path(p).resolve(strict=True) for p in paths]
    names=[plugin_name(p.name) for p in paths]
    if not names or len(set(names))!=len(names):raise ValueError("supply distinct plugins in active load order, masters first")
    issues=[];counts=Counter();winning={};reports=[];total=0;incomplete=False
    def issue(code,provider,offset,detail,severity="error"):
        nonlocal incomplete
        counts[severity]+=1
        if len(issues)<max_issues:issues.append({"code":code,"severity":severity,"plugin":provider,"offset":offset,"detail":detail})
        else:incomplete=True
    for path,name in zip(paths,names):
        records={};pending=[];group_count=0;local_count=0;before=sum(counts.values())
        try:
            with path.open("rb") as f:
                end=path.stat().st_size
                def read(n):
                    b=f.read(n)
                    if len(b)!=n:raise ValueError("truncated file")
                    return b
                sig,n,flags,form,*_=HEADER.unpack(read(24))
                if sig!=b"TES4" or form or n>MAX_RECORD or n+24>end:raise ValueError("not a bounded FNV TES4 header")
                masters=[plugin_name(text(v)) for k,v in subs(read(n)) if k==b"MAST"]
                if len(set(masters+[name]))!=len(masters)+1:raise ValueError("duplicate masters")
                for m in masters:
                    if m not in names[:names.index(name)]:issue("master-order",name,0,"Missing or later master: "+m)
                slots=masters+[name]
                def fid(v,off):
                    if not v or v>>24>=len(slots) or not v&0xffffff:
                        issue("invalid-formid",name,off,f"{v:08X}");return None
                    return (slots[v>>24],v&0xffffff)
                def val32(b,off):
                    if len(b)!=4:issue("field-size",name,off,"Expected 4-byte FormID");return None
                    return fid(struct.unpack("<I",b)[0],off) if b!=bytes(4) else None
                def walk(bound,parents=()):
                    nonlocal group_count,local_count,total
                    if len(parents)>64:raise ValueError("group nesting limit")
                    seen=set();prev=None;last_rank=-1;last_bucket=-1
                    while f.tell()<bound:
                        off=f.tell()
                        if bound-off<24:raise ValueError("truncated header")
                        h=read(24);sig,n,flags,raw,*_=HEADER.unpack(h)
                        total+=1
                        if total>max_records:raise ValueError("record/group limit exceeded")
                        if sig==b"GRUP":
                            _,_,label,typ,_,_=struct.unpack("<4sI4sIII",h)
                            if n<24 or off+n>bound:raise ValueError("group length exceeds parent")
                            group_count+=1
                            key=fid(struct.unpack("<I",label)[0],off) if typ in (1,6,7,8,9,10) else struct.unpack("<hh",label) if typ in (4,5) else struct.unpack("<i",label)[0] if typ in (2,3) else label.decode("ascii",errors="replace")
                            parent=parents[-1] if parents else None;pt=parent[0] if parent else None
                            if (typ,key) in seen:issue("duplicate-group",name,off,f"Repeated sibling group {typ}:{key}")
                            seen.add((typ,key))
                            legal=(typ==0 and pt is None or typ==1 and parent==(0,"WRLD") or typ==2 and parent==(0,"CELL") or typ==3 and pt==2 or typ==4 and pt==1 or typ==5 and pt==4 or typ==6 and pt in (1,3,5) or typ==7 and parent==(0,"DIAL") or typ in (8,9,10) and pt==6)
                            if not legal:issue("group-parent",name,off,f"Group {typ} under {parent}")
                            if typ in (1,6,7):
                                expected={1:"WRLD",6:"CELL",7:"DIAL"}[typ]
                                if prev!=(expected,key):issue("owner-order",name,off,f"Group {typ} does not immediately follow its {expected} {key}")
                                pending.append((key,{expected},off,"group-owner"))
                            if typ in (8,9,10):
                                if parent!=(6,key):issue("child-owner",name,off,"Child bucket label differs from cell owner")
                                if typ<last_bucket:issue("bucket-order",name,off,"Cell child buckets out of conventional order","warning")
                                last_bucket=typ
                            if typ==5 and pt==4 and (key[0]//4,key[1]//4)!=parent[1]:issue("subblock-coordinate",name,off,f"Sub-block {key} outside block {parent[1]}")
                            if typ==0 and key in TOP:
                                rank=TOP.index(key)
                                if rank<last_rank:issue("top-order",name,off,"Top-level groups differ from conventional FNV order","warning")
                                last_rank=rank
                            walk(off+n,parents+((typ,key),))
                            prev=None;continue
                        if n>MAX_RECORD or f.tell()+n>bound:raise ValueError("record exceeds parent")
                        kind=sig.decode("ascii");identity=fid(raw,off);local_count+=1
                        data=read(n) if kind in KINDS or quest_links and kind in ("QUST","DIAL","INFO") else None
                        if data is None:f.seek(n,1)
                        pt,key=parents[-1] if parents else (None,None)
                        world=next((v for t,v in parents if t==1),None)
                        owner=next((v for t,v in reversed(parents) if t==6),None)
                        if not parents or pt==0 and kind!=key or pt in (2,4,6) or pt in (3,5) and kind!="CELL" or pt==1 and kind not in ("CELL","ROAD") or pt==7 and kind!="INFO" or pt in (8,9) and kind not in REFS|{"LAND","NAVM"} or pt==10 and kind!="REFR":
                            issue("record-parent",name,off,f"{kind} in group {pt}:{key}")
                        if kind in ("LAND","NAVM") and pt!=9:issue("temporary-owner",name,off,f"{kind} must be in temporary cell children")
                        if kind in REFS and pt in (8,9) and bool(flags&PERSISTENT)!=(pt==8):issue("persistence",name,off,"Reference persistent flag disagrees with bucket","warning")
                        item={"kind":kind,"flags":flags,"provider":name,"offset":off,"world":world,"owner":owner,"coords":None,"links":[]}
                        if kind=="INFO":item["topic"]=key if pt==7 else None
                        if identity in records:issue("duplicate-formid",name,off,str(identity))
                        if identity:records[identity]=item
                        if data is not None and not flags&DELETED:
                            if flags&0x40000:
                                if len(data)<4:raise ValueError("short compressed record")
                                size=struct.unpack_from("<I",data)[0]
                                if size>MAX_RECORD:raise ValueError("compressed record exceeds limit")
                                d=zlib.decompressobj();data=d.decompress(data[4:],size+1)
                                if len(data)!=size or not d.eof or d.unused_data or d.unconsumed_tail:raise ValueError("invalid compressed record")
                            parts=list(subs(data));fields=dict(parts)
                            if quest_links and kind in ("QUST","DIAL","INFO"):
                                from .quest_remap_schema import fields as quest_fields
                                try:exact=quest_fields(sig,parts)
                                except (ValueError,UnicodeError,struct.error):
                                    issue("opaque-quest-layout",name,off,"Quest layout outside generated schema","warning")
                                else:
                                    for i,offset,kinds in exact:
                                        tag,value=parts[i];target=val32(value[offset:offset+4],off)
                                        if target:item["links"].append((target,set(kinds),"quest-"+tag.decode("ascii").lower()))
                                        if kind=="INFO" and tag==b"TPIC" and target!=item.get("topic"):
                                            issue("info-topic-mismatch",name,off,"TPIC differs from group owner")
                            if kind=="CELL":
                                if b"XCLC" in fields:
                                    v=fields[b"XCLC"]
                                    if len(v) not in (8,12):issue("cell-coordinates",name,off,"Invalid XCLC size")
                                    else:item["coords"]=struct.unpack_from("<ii",v)
                                if pt==5:
                                    if item["coords"] is None:issue("missing-coordinates",name,off,"Exterior cell lacks XCLC")
                                    else:
                                        x,y=item["coords"]
                                        if (y//8,x//8)!=key or (4,(y//32,x//32)) not in parents:issue("cell-grid",name,off,f"Cell {(x,y)} in wrong block/sub-block")
                                    if flags&PERSISTENT:issue("persistent-cell",name,off,"Persistent world cell inside exterior block")
                                elif pt==1 and not flags&PERSISTENT:issue("persistent-cell",name,off,"Direct world child CELL is not persistent")
                                elif pt==3 and identity:
                                    local=identity[1]
                                    if key!=(local//10)%10 or (2,local%10) not in parents:issue("interior-grid",name,off,"Interior cell in wrong FormID block/sub-block")
                            if kind=="REFR" and any(tag in fields for tag in (b"XPOD",b"XPTL",b"XRMR",b"XLRM",b"XNDP")):
                                from .fnv_portal_fields import inspect as marker_fields
                                try:marker,edges=marker_fields(parts)
                                except (ValueError,struct.error) as exc:issue("native-marker-layout",name,off,str(exc),"warning")
                                else:
                                    item["marker"]=marker
                                    for i,offset,kinds in edges:
                                        tag,value=parts[i];target=val32(value[offset:offset+4],off)
                                        if target:item["links"].append((target,set(kinds),"marker-"+tag.decode("ascii").lower()))
                            if kind in REFS:
                                if b"NAME" in fields:
                                    target=val32(fields[b"NAME"],off)
                                    if target:item["base"]=target
                                    if target:item["links"].append((target,{"NPC_"} if kind=="ACHR" else {"CREA"} if kind=="ACRE" else None,"base-object"))
                                    else:issue("missing-base",name,off,"Null or invalid NAME")
                                else:issue("missing-base",name,off,"No NAME subrecord")
                                if b"XLKR" in fields:
                                    link=val32(fields[b"XLKR"],off)
                                    if link:item["links"].append((link,REFS,"linked-reference"))
                                if kind=="REFR" and b"XTEL" in fields:
                                    value=fields[b"XTEL"]
                                    if len(value)!=32:issue("teleport-size",name,off,"Expected 32-byte XTEL")
                                    else:
                                        target=val32(value[:4],off);coords=struct.unpack_from("<6fI",value,4)
                                        if not target or not all(math.isfinite(x) for x in coords[:6]) or coords[-1]&~1:issue("teleport-destination",name,off,"Invalid teleport destination")
                                        else:
                                            item["teleport"]=target;item["links"].append((target,{"REFR"},"teleport"))
                                if kind=="REFR" and b"DATA" in fields and len(fields[b"DATA"])==24 and pt==9:
                                    x,y,*_=struct.unpack("<6f",fields[b"DATA"])
                                    if math.isfinite(x) and math.isfinite(y):item["position"]=(math.floor(x/4096),math.floor(y/4096))
                                    else:issue("reference-position",name,off,"Nonfinite reference transform")
                            if kind=="LAND":
                                from .texture_budget import audit
                                budget=audit(parts,"newvegas")
                                for q in budget["quadrants"]:
                                    if q["over_budget"]:issue("land-texture-budget",name,off,f"Quadrant {q['quadrant']}: {q['allocated']} allocated, limit {q['limit']}")
                                    for detail in q["issues"]:issue("land-alpha-layer",name,off,f"Quadrant {q['quadrant']}: {detail}")
                                for detail in budget["issues"]:issue("land-alpha-layer",name,off,detail)
                                quadrants=set()
                                for k,v in parts:
                                    if k in (b"BTXT",b"ATXT"):
                                        if len(v)!=8:issue("land-layer-size",name,off,"Invalid texture layer");continue
                                        target=val32(v[:4],off)
                                        if target:item["links"].append((target,{"LTEX"},"land-texture"))
                                        if v[4]>3:issue("land-quadrant",name,off,"Invalid quadrant")
                                        if k==b"BTXT":
                                            if v[4] in quadrants:issue("duplicate-base-layer",name,off,"Repeated base quadrant")
                                            quadrants.add(v[4])
                                    elif k==b"VTEX":
                                        if len(v)%4:issue("land-layer-size",name,off,"Invalid VTEX")
                                        else:
                                            for j in range(0,len(v),4):
                                                target=val32(v[j:j+4],off)
                                                if target:item["links"].append((target,{"LTEX"},"land-texture"))
                                for k,size in ((b"VHGT",1096),(b"VNML",3267),(b"VCLR",3267)):
                                    if k in fields and len(fields[k])!=size:issue("land-field-size",name,off,k.decode())
                            if kind=="LTEX" and b"TNAM" in fields:
                                target=val32(fields[b"TNAM"],off)
                                if target:item["links"].append((target,{"TXST"},"texture-set"))
                        prev=(kind,identity)
                    if f.tell()!=bound:raise ValueError("group boundary mismatch")
                walk(end)
            for target,types,off,role in pending:
                item=records.get(target) or winning.get(target)
                if item is None or item["kind"] not in types:issue(role,name,off,f"Unresolved or wrong-type owner {target}")
            for identity,item in records.items():
                old=winning.get(identity)
                if old:
                    if old["kind"]!=item["kind"]:issue("override-signature",name,item["offset"],str(identity))
                    if item["kind"] in ("CELL","LAND","NAVM") and (old["world"],old["owner"],old["coords"])!=(item["world"],item["owner"],item["coords"]) and not item["flags"]&DELETED and not old["flags"]&DELETED:
                        issue("override-relocation",name,item["offset"],f"{identity} changes world/cell/coordinates; review merge","warning")
                winning[identity]=item
            reports.append({"plugin":name,"records":local_count,"groups":group_count,"issues":sum(counts.values())-before})
        except (ValueError,struct.error,UnicodeError,zlib.error,OSError) as exc:
            issue("parse-error",name,0,str(exc));incomplete=True
    def live(id): 
        r=winning.get(id)
        return r if r and not r["flags"]&DELETED else None
    coords={};persistent={};lands={};interiors=0;persistent_refs=0
    for identity,r in winning.items():
        if r["flags"]&DELETED:continue
        name,off,kind=r["provider"],r["offset"],r["kind"]
        for target,types,role in r["links"]:
            t=live(target)
            if t is None or types and t["kind"] not in types or role=="base-object" and t["kind"] in {"WRLD","CELL","LAND","NAVM","ROAD","LTEX","TXST","REFR","ACHR","ACRE"}:issue("unresolved-"+role,name,off,f"{identity} -> {target}")
        if "marker" in r:
            for target,types,role in r["links"]:
                if role in ("marker-xpod","marker-xlrm"):
                    other=live(target)
                    if other and (target==identity or other["owner"]!=r["owner"] or "room_header" not in other.get("marker",{})):
                        issue("room-marker-target",name,off,"Room marker target must be a distinct room in the same cell","warning")
                if role=="marker-xndp":
                    other=live(target)
                    if other and other["owner"]!=r["owner"]:issue("nav-door-owner",name,off,"Navigation mesh is in another cell","warning")
        if "teleport" in r:
            target=r["teleport"];other=live(target);base=live(r.get("base"))
            if not base or base["kind"]!="DOOR":issue("teleport-base",name,off,"Teleport source is not a door")
            if other:
                destination=live(other.get("base"))
                if not destination or destination["kind"]!="DOOR":issue("teleport-target-base",name,off,"Teleport target is not a door")
                if target==identity or other.get("teleport")!=identity:issue("teleport-reciprocity",name,off,"Nonreciprocal teleport link","warning")
                if not r["flags"]&PERSISTENT or not other["flags"]&PERSISTENT:issue("teleport-persistence",name,off,"Teleport endpoint not persistent","warning")
        if quest_links and kind=="INFO":
            topic=live(r.get("topic"))
            if not topic or topic["kind"]!="DIAL":issue("orphan-topic",name,off,str(identity))
            for target,types,role in r["links"]:
                if role=="quest-pnam":
                    previous=live(target)
                    if previous and previous.get("topic")!=r.get("topic"):issue("previous-info-topic",name,off,str(target))
        if r["world"] is not None and (not live(r["world"]) or live(r["world"])["kind"]!="WRLD"):issue("orphan-world",name,off,str(identity))
        if r["owner"] is not None:
            c=live(r["owner"])
            if not c or c["kind"]!="CELL":issue("orphan-cell",name,off,str(identity))
            else:
                if c["world"]!=r["world"]:issue("world-owner-mismatch",name,off,str(identity))
                if c["coords"] is not None and not c["flags"]&PERSISTENT and c["world"] is not None and "position" in r and r["position"]!=c["coords"]:issue("reference-grid",name,off,f"Reference at {r['position']} assigned to {c['coords']}","warning")
        if kind=="CELL" and r["world"] is None:interiors+=1
        if kind in REFS and r["flags"]&PERSISTENT:persistent_refs+=1
        if kind=="CELL" and r["world"] is not None:
            table,key=(persistent,r["world"]) if r["flags"]&PERSISTENT else (coords,(r["world"],r["coords"]))
            if key in table:issue("duplicate-persistent-cell" if table is persistent else "duplicate-cell-coordinate",name,off,f"{identity} and {table[key]}")
            table[key]=identity
        if kind=="LAND" and r["owner"] is not None:
            if r["owner"] in lands:issue("duplicate-land",name,off,f"{identity} and {lands[r['owner']]}")
            lands[r["owner"]]=identity
    return {"game":"newvegas","valid":not counts["error"] and not incomplete,"complete":not incomplete,"errors":counts["error"],"warnings":counts["warning"],"issues":issues,"plugins":reports,"winning_records":len(winning),"exterior_cells":len(coords),"persistent_cells":len(persistent),"interior_cells":interiors,"persistent_references":persistent_refs,"land_records":len(lands),"room_markers":sum(1 for r in winning.values() if "room_header" in r.get("marker",{}) and not r["flags"]&DELETED),"portal_markers":sum(1 for r in winning.values() if "portal_rooms" in r.get("marker",{}) and not r["flags"]&DELETED),"teleport_references":sum(1 for r in winning.values() if "teleport" in r and not r["flags"]&DELETED),"quest_links_checked":quest_links,"scope":"FNV hierarchy and selected references; not a complete schema or engine validator; no modifications"}
