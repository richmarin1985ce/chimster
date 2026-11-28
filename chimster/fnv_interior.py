"""Experimental FNV interior cell and static placement fixture writer."""
from pathlib import Path
import struct,math
from .fnv_content import ident,static,reference,bounds,asset
from .fnv_patch import sub,record
from .fnv_world import cstr,group
from .fnv_bindings import Bindings
from .formids import FormIDs
from .fnv_records import scan,subs
from .interior_layout import point,validate as validate_layout

def export(spec,output,masters=(),allocator=None):
    if spec.get("schema")!=1 or set(spec)-{"schema","cells","statics","doors"}:
        raise ValueError("invalid interior specification")
    p=Path(output)
    if p.suffix.lower()!=".esp" or p.exists() or p.is_symlink():
        raise ValueError("expected new ESP")
    cells=spec["cells"];statics=spec.get("statics",[]);doors=spec.get("doors",[])
    if not isinstance(cells,list) or not 1<=len(cells)<=10000 or not isinstance(statics,list) or len(statics)>50000 or not isinstance(doors,list) or len(doors)>50000:
        raise ValueError("interior size limit")
    b=Bindings(masters,p);ids=allocator or FormIDs(p.name)
    base={};base_types={};top=[];door_top=[];blocks={};used=set();expected={};placements={};portal_bindings=[];native_bindings=[];marker_ids={}
    def alloc(kind,key):
        ident(key)
        return b.slot|ids.get(kind+"/"+key.casefold())
    def register(key):
        ident(key)
        if key.casefold() in used:raise ValueError("duplicate editor ID")
        used.add(key.casefold())
    for s in statics:
        register(s["id"]);fid=alloc("STAT",s["id"])
        base[s["id"]]=fid;base_types[s["id"]]="STAT";top.append(static(fid,s));expected[fid]="STAT"
    for door in doors:
        if set(door)-{"id","title","bounds","model","flags"}:raise ValueError("unknown door field")
        register(door["id"]);fid=alloc("DOOR",door["id"])
        flags=door.get("flags",0)
        if type(flags) is not int or flags&~0x1e:raise ValueError("unsupported door flags")
        body=sub(b"EDID",ident(door["id"]))+bounds(door["bounds"])+sub(b"FULL",cstr(door["title"]))+sub(b"MODL",asset(door["model"],".nif"))+sub(b"FNAM",bytes([flags]))
        door_top.append(record(b"DOOR",body,fid));expected[fid]="DOOR"
        base[door["id"]]=fid;base_types[door["id"]]="DOOR"
    count=0;groups=1+bool(top)+bool(door_top);cell_ids={}
    for cell in cells:
        if set(cell)-{"id","title","placements","layout","portal_doors","native_markers"}:raise ValueError("unknown cell fields")
        register(cell["id"]);cid=alloc("CELL",cell["id"]);cell_ids[cell["id"]]=cid;expected[cid]="CELL"
        for r in cell.get("placements",[]):
            ident(r["id"]);key=cell["id"]+"/"+r["id"]
            fid=b.slot|ids.get("REFR/"+key.casefold())
            if count>=50000:raise ValueError("placement limit")
            count+=1
            if isinstance(r["base"],str):
                if r["base"] not in base:raise ValueError("unknown base")
                target=base[r["base"]];kind=base_types[r["base"]]
            else:
                target=b.resolve(r["base"],{"STAT","DOOR"})
                identity=b.slots.decode(target)
                kind=b.records[(identity.origin,identity.local)]["signature"]
            placements[key]=(fid,r,target,kind)
    # Native markers are explicit template-derived payloads, never inferred from
    # portable geometry or hard-coded game master IDs.
    for cell in cells:
        markers=cell.get("native_markers",[])
        if not isinstance(markers,list) or len(markers)>10000:raise ValueError("marker limit")
        if markers and "layout" not in cell:raise ValueError("native markers require portable layout")
        for m in markers:
            if not isinstance(m,dict) or set(m)-{"id","kind","base","position","rotation","primitive_hex","collision_layer","header_tail_hex","linked_rooms","rooms","geometry_hex","geometry_convention"}:raise ValueError("unknown native marker fields")
            kind=m["kind"];ident(m["id"])
            if kind not in ("room","portal"):raise ValueError("unknown native marker kind")
            key=(cell["id"],kind,m["id"])
            if key in marker_ids:raise ValueError("duplicate native marker")
            fid=b.slot|ids.get("REFR/"+cell["id"].casefold()+"/marker/"+kind+"/"+m["id"].casefold())
            base_id=b.resolve(m["base"],{"STAT"})
            identity=b.slots.decode(base_id)
            editor=b.records[(identity.origin,identity.local)]["editor_id"]
            required="roommarker" if kind=="room" else "portalmarker"
            if not editor or editor.casefold()!=required:raise ValueError("marker base must be explicit RoomMarker or PortalMarker STAT")
            marker_ids[key]=(fid,base_id,m)
            if len(marker_ids)>50000:raise ValueError("total native marker limit")
    def link(key):
        if not isinstance(key,str) or key not in placements:raise ValueError("unknown local placement link")
        return placements[key]
    for cell in cells:
        cid=cell_ids[cell["id"]]
        if "layout" in cell:
            layout=cell["layout"]
            if not validate_layout(layout)["valid"]:raise ValueError("invalid portable room layout")
            portals={p["id"]:p for p in layout.get("portals",[])}
            for pid,rid in cell.get("portal_doors",{}).items():
                if pid not in portals:raise ValueError("unknown portal")
                fid,r,_,kind=link(cell["id"]+"/"+rid)
                if kind!="DOOR" or "teleport" in r:raise ValueError("visibility portal requires non-teleport door")
                corners=portals[pid]["corners"];position=point(r["position"])
                if any(not min(c[i] for c in corners)-1e-5<=position[i]<=max(c[i] for c in corners)+1e-5 for i in range(3)):
                    raise ValueError("door outside portal rectangle")
                portal_bindings.append({"cell":cell["id"],"portal":pid,"door":rid,"local_id":fid&0xffffff})
        elif cell.get("portal_doors"):raise ValueError("portal bindings require layout")
        payload=sub(b"EDID",ident(cell["id"]))+sub(b"FULL",cstr(cell["title"]))+sub(b"DATA",b"\x01")
        raw=record(b"CELL",payload,cid)
        buckets={8:[],9:[]}
        for r in cell.get("placements",[]):
            if set(r)-{"id","base","position","yaw","scale","persistent","linked_ref","teleport"}:raise ValueError("unknown placement field")
            persistent=r.get("persistent",False)
            if type(persistent) is not bool:raise ValueError("invalid persistence flag")
            key=cell["id"]+"/"+r["id"];fid,_,target,kind=link(key)
            x,y,z=point(r["position"])
            placed=reference(fid,target,x,y,z,r.get("yaw",0.),r.get("scale",1.))
            parts=dict(subs(placed[24:]))
            payload=sub(b"NAME",parts[b"NAME"])
            if "teleport" in r:
                tele=r["teleport"]
                if not isinstance(tele,dict) or set(tele)!={"target","arrival","yaw"}:raise ValueError("explicit teleport arrival and yaw required")
                other,other_row,_,other_kind=link(tele["target"])
                if kind!="DOOR" or other_kind!="DOOR" or other==fid or not persistent or other_row.get("persistent") is not True:
                    raise ValueError("teleport requires distinct persistent door endpoints")
                reverse=other_row.get("teleport")
                if not isinstance(reverse,dict) or reverse.get("target")!=key:raise ValueError("teleport endpoints must be reciprocal")
                arrival=point(tele["arrival"]);yaw=tele["yaw"]
                if type(yaw) not in (int,float) or not math.isfinite(yaw) or abs(yaw)>36000:raise ValueError("invalid arrival yaw")
                payload+=sub(b"XTEL",struct.pack("<I6fI",other,*arrival,0.,0.,math.radians(yaw),0))
            if "linked_ref" in r:
                other,_,_,_=link(r["linked_ref"])
                if other==fid:raise ValueError("self linked reference")
                payload+=sub(b"XLKR",struct.pack("<I",other))
            payload+=sub(b"XSCL",parts[b"XSCL"])+sub(b"DATA",parts[b"DATA"])
            placed=record(b"REFR",payload,fid)
            if persistent:
                placed=placed[:8]+struct.pack("<I",0x400)+placed[12:]
            buckets[8 if persistent else 9].append(placed);expected[fid]="REFR"
        from .fnv_portal_fields import inspect as inspect_marker
        if cell.get("native_markers"):
            room_ids={r["id"] for r in cell["layout"]["rooms"]}
            portal_map={r["id"]:r for r in cell["layout"].get("portals",[])}
            def room_target(rid):
                key=(cell["id"],"room",rid)
                if key not in marker_ids:raise ValueError("native room endpoint missing")
                return marker_ids[key][0]
            for m in cell["native_markers"]:
                kind=m["kind"];mid=m["id"]
                fid,base_id,_=marker_ids[(cell["id"],kind,mid)]
                pos=point(m["position"]);rotation=point(m["rotation"])
                prim=bytes.fromhex(m["primitive_hex"])
                fields=[(b"NAME",struct.pack("<I",base_id)),(b"XPRM",prim)]
                if "collision_layer" in m:
                    layer=m["collision_layer"]
                    if type(layer) is not int or not 0<=layer<=0xffffffff:raise ValueError("invalid collision layer")
                    fields.append((b"XTRI",struct.pack("<I",layer)))
                if kind=="room":
                    if mid not in room_ids or set(m)&{"rooms","geometry_hex","geometry_convention"}:raise ValueError("room marker does not match layout")
                    linked=m.get("linked_rooms",[])
                    if not isinstance(linked,list) or len(linked)>65535 or mid in linked:raise ValueError("invalid room links")
                    tail=bytes.fromhex(m["header_tail_hex"])
                    if len(tail)!=2:raise ValueError("explicit room header bytes required")
                    fields.append((b"XRMR",struct.pack("<H",len(linked))+tail))
                    fields.extend((b"XLRM",struct.pack("<I",room_target(rid))) for rid in linked)
                else:
                    if mid not in portal_map or set(m)&{"header_tail_hex","linked_rooms"}:raise ValueError("portal marker does not match layout")
                    rooms=m["rooms"]
                    if not isinstance(rooms,list) or len(rooms)!=2 or set(rooms)!=set(portal_map[mid]["rooms"]):raise ValueError("portal endpoints differ from portable layout")
                    fields.extend(((b"XPOD",struct.pack("<2I",*(room_target(rid) for rid in rooms))),
                                   (b"XPTL",bytes.fromhex(m["geometry_hex"]))))
                fields.extend(((b"XSCL",struct.pack("<f",1.)),(b"DATA",struct.pack("<6f",*pos,*rotation))))
                decoded,_=inspect_marker(fields)
                if decoded["primitive"]["type"]!=(1 if kind=="room" else 3):raise ValueError("unexpected primitive type for marker")
                if kind=="portal" and "geometry_convention" in m:
                    from .native_visibility_geometry import rectangle,Mapping
                    convention=m["geometry_convention"]
                    if not isinstance(convention,dict) or set(convention)!={"order","plane","dimension_factor"}:raise ValueError("explicit portal geometry convention required")
                    corners=rectangle(decoded["portal_geometry"],Mapping(((1,0,0),(0,1,0),(0,0,1)),1),**convention)
                    expected_corners=portal_map[mid]["corners"]
                    if any(not any(math.dist(a,b)<=1e-4 for b in expected_corners) for a in corners) or any(not any(math.dist(a,b)<=1e-4 for b in corners) for a in expected_corners):
                        raise ValueError("native portal rectangle differs from portable layout")
                buckets[9].append(record(b"REFR",b"".join(sub(tag,value) for tag,value in fields),fid))
                expected[fid]="REFR";native_bindings.append({"cell":cell["id"],"kind":kind,"layout_id":mid,"local_id":fid&0xffffff})
        children=b"".join(group(kind,cid,b"".join(rows)) for kind,rows in buckets.items() if rows)
        if children:
            raw+=group(6,cid,children);groups+=1+sum(bool(rows) for rows in buckets.values())
        local=cid&0xffffff
        blocks.setdefault(local%10,{}).setdefault((local//10)%10,[]).append(raw)
    nested=[]
    for block,subs in sorted(blocks.items()):
        chunks=[group(3,subblock,b"".join(rows)) for subblock,rows in sorted(subs.items())]
        nested.append(group(2,block,b"".join(chunks)));groups+=1+len(chunks)
    body=(group(0,b"DOOR",b"".join(door_top)) if door_top else b"")+(group(0,b"STAT",b"".join(top)) if top else b"")+group(0,b"CELL",b"".join(nested))
    header=record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,len(expected)+groups,ids.next))+sub(b"CNAM",b"Chimster\0")+b.header())
    b.check();created=False
    try:
        with p.open("xb") as stream:
            created=True;stream.write(header+body)
        report=scan(p)
        if len(report["records"])!=len(expected) or {b.slot|r["local_id"]:r["signature"] for r in report["records"]}!=expected:
            raise ValueError("interior record identity mismatch")
        from .world_validator import validate
        validation=validate([*b.paths,p])
        if not validation["valid"]:raise ValueError("interior hierarchy validation failed")
        b.check()
    except Exception:
        if created:p.unlink()
        raise
    return {"output":str(p),"cells":len(cells),"placements":count,"records":len(expected),"portal_bindings":portal_bindings,"native_marker_bindings":native_bindings,"doors":len(door_top),"scope":"experimental generated FNV interiors and door links; template-derived native room and portal records; geometry conventions and runtime behavior unverified"}
