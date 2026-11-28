"""Conservative structural editing; preserve untouched record payloads."""
import hashlib
import math
import re
import secrets
import struct
from dataclasses import replace
from .mcp_extended import native_session, ReferenceProposals, REFERENCE_PROFILES
from .native_serialization import serialize
from .native_editor import NativeSession
from .native_identity import token
from .record_graph import Identity
from .loadorder import plugin_name

def sub(tag,value):
    if len(value)>65535:raise ValueError("oversized field")
    return struct.pack("<4sH",tag,len(value))+value

def payload(parts):
    return b"".join(sub(k,v) for k,v in parts)

def group_type(n):
    return struct.unpack_from("<i",n.header,12)[0] if n.signature==b"GRUP" else -1

def tree_edit(nodes,replacements,additions,removed=(),prefix=()):
    result=[]
    for i,n in enumerate(nodes):
        path=prefix+(i,)
        if path in removed:continue
        if path in replacements:n=replacements[path]
        if n.signature==b"GRUP":
            n=replace(n,children=tree_edit(n.children,replacements,additions,removed,path)+tuple(additions.get(path,())))
        result.append(n)
    return tuple(result)

def globalspec(row):
    parts=row["parts"]
    if len(parts)!=3 or {k for k,v in parts}!={b"EDID",b"FNAM",b"FLTV"}:
        raise ValueError("only exact simple GLOB layouts supported")
    fields=dict(parts)
    if fields[b"FNAM"] not in (b"s",b"l",b"f") or len(fields[b"FLTV"])!=4:
        raise ValueError("unknown global layout")
    edid=fields[b"EDID"]
    if not re.fullmatch(rb"[A-Za-z][A-Za-z0-9_]{0,63}\x00",edid):raise ValueError("unsupported editor ID")
    val=struct.unpack("<f",fields[b"FLTV"])[0]
    if not math.isfinite(val):raise ValueError("invalid global value")
    return parts,fields,val

def set_field(parts,tag,data):
    return payload([(k,data if k==tag else v) for k,v in parts])

def update_header(session,next_id):
    from .native_parser import subrecords
    n=session.nodes[0]
    parts=list(subrecords(session.profile,n))
    matches=[v for k,v in parts if k==b"HEDR"]
    if len(matches)!=1 or len(matches[0])!=12:raise ValueError("unsupported header")
    version,count,cursor=struct.unpack("<fII",matches[0])
    def count_nodes(nodes):
        return sum(1+count_nodes(n.children) for n in nodes)
    if count!=count_nodes(session.nodes[1:]) or cursor>=0xffffff or cursor==0:
        raise ValueError("inconsistent header count or allocation cursor")
    if next_id<cursor or next_id>=0xffffff:raise ValueError("invalid next ID")
    return replace(n,payload=set_field(parts,b"HEDR",struct.pack("<fII",version,count+1,next_id)))

class StructureProposals(ReferenceProposals):
    def preview(self,id,identity,operation,revision,sha256,new_edid="",value="",destination="",x=0,y=0,z=0):
        self.pending=None
        m,a,s,_=native_session(self.project,id)
        name=a["filename"]
        if s.profile not in REFERENCE_PROFILES or m["revision"]!=revision or a["sha256"]!=sha256:
            raise ValueError("stale or unsupported plugin")
        if not name.lower().endswith(".esp") or not re.fullmatch(r"[A-Za-z0-9_. -]+",name) or name.split(".")[0].strip().upper() in {"CON","PRN","AUX","NUL",*[f"COM{i}" for i in range(1,10)],*[f"LPT{i}" for i in range(1,10)]}:
            raise ValueError("unsafe plugin filename")
        if struct.unpack_from("<I",s.nodes[0].header,8)[0]!=0:raise ValueError("plain full-slot ESP only")
        own=plugin_name(name)
        path=s.resolve_identity(identity);row=s.rows[path];node=s.node(path)
        key=row["key"]
        if key.origin!=own or struct.unpack_from("<I",node.header,8)[0]!=0:
            raise ValueError("only unflagged owned records supported")
        def records(session):
            if len(session.rows)!=len(session.paths) or any(len(v)!=1 for v in session.paths.values()):
                raise ValueError("missing or duplicate persistent identity")
            return {k:(session.node(v[0]).signature,session.node(v[0]).header[8:],session.node(v[0]).payload) for k,v in session.paths.items()}
        before=records(s)
        edits={};adds={};remove=();changed=key;new_key=None
        if operation in ("duplicate-global","set-global"):
            if node.signature!=b"GLOB" or len(path)!=2 or group_type(s.node(path[:-1]))!=0 or s.node(path[:-1]).header[8:12]!=b"GLOB":
                raise ValueError("top-level GLOB required")
            parts,fields,old=globalspec(row)
            if operation=="duplicate-global":
                if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}",new_edid):raise ValueError("invalid editor ID")
                if any(k==b"EDID" and v.rstrip(b"\0").lower()==new_edid.lower().encode() for r in s.rows.values() for k,v in r["parts"]):
                    raise ValueError("duplicate editor ID")
                from .native_parser import subrecords
                h=[v for k,v in subrecords(s.profile,s.nodes[0]) if k==b"HEDR"]
                if len(h)!=1 or len(h[0])!=12:raise ValueError("invalid HEDR")
                cursor=struct.unpack_from("<I",h[0],8)[0]
                local=max(0x800,cursor,max((k.local for k in before if k.origin==own),default=0)+1)
                if local>=0xfffffe:raise ValueError("ID space exhausted")
                new_key=Identity(own,local)
                header=bytearray(node.header);struct.pack_into("<I",header,12,s.slots.encode(new_key))
                clone=replace(node,header=bytes(header),payload=set_field(parts,b"EDID",new_edid.encode()+b"\0"))
                edits[(0,)]=update_header(s,local+1);adds[path[:-1]]=[clone]
                summary={"new_identity":token(s.profile,new_key),"editor_id":new_edid,"value":old}
                changed=None
            else:
                val=float(value)
                kind=fields[b"FNAM"]
                if not math.isfinite(val) or abs(val)>3.4e38 or kind!=b"f" and (not val.is_integer() or abs(val)> (32767 if kind==b"s" else 16777216)):
                    raise ValueError("value outside global type range")
                raw=struct.pack("<f",val)
                edits[path]=replace(node,payload=set_field(parts,b"FLTV",raw))
                summary={"before":old,"after":struct.unpack("<f",raw)[0]}
        elif operation=="relocate-reference":
            if s.profile!="new-vegas" or node.signature!=b"REFR" or len(path)<4:
                raise ValueError("FNV exterior reference required")
            dest=s.resolve_identity(destination);cell=s.node(dest)
            if cell.signature!=b"CELL" or s.rows[dest]["key"].origin!=own or struct.unpack_from("<I",cell.header,8)[0]!=0:
                raise ValueError("owned nonpersistent destination CELL required")
            # Existing temporary child groups only; never manufacture hierarchy.
            def temporary(cellpath):
                target=s.node(cellpath);fid=target.header[12:16]
                siblings=s.node(cellpath[:-1]).children
                matches=[cellpath[:-1]+(i,) for i,n in enumerate(siblings) if group_type(n)==6 and n.header[8:12]==fid]
                if len(matches)!=1:raise ValueError("missing cell children group")
                g=matches[0]
                matches=[g+(i,) for i,n in enumerate(s.node(g).children) if group_type(n)==9 and n.header[8:12]==fid]
                if len(matches)!=1:raise ValueError("missing temporary cell group")
                return matches[0]
            source_parent=path[:-1]
            if group_type(s.node(source_parent))!=9:raise ValueError("temporary reference required")
            cell_group=source_parent[:-1];label=s.node(cell_group).header[8:12]
            if group_type(s.node(cell_group))!=6 or s.node(source_parent).header[8:12]!=label:raise ValueError("invalid source cell group")
            parent=cell_group[:-1]
            cells=[parent+(i,) for i,n in enumerate(s.node(parent).children) if n.signature==b"CELL" and n.header[12:16]==label]
            if len(cells)!=1 or temporary(cells[0])!=source_parent:raise ValueError("invalid source ownership")
            def world(p):
                matches=[s.node(p[:i]).header[8:12] for i in range(1,len(p)) if group_type(s.node(p[:i]))==1]
                if len(matches)!=1:raise ValueError("exterior world required")
                return matches[0]
            target_parent=temporary(dest)
            if target_parent==source_parent or world(path)!=world(dest):raise ValueError("different cell in same world required")
            def grid(p):
                values=[v for k,v in s.rows[p]["parts"] if k==b"XCLC"]
                if len(values)!=1 or len(values[0])!=12:raise ValueError("exterior grid required")
                return struct.unpack_from("<ii",values[0])
            parts=row["parts"]
            fields=dict(parts)
            if len(fields)!=len(parts) or not {b"NAME",b"DATA"}<=set(fields) or set(fields)-{b"NAME",b"DATA",b"XSCL"} or len(fields[b"NAME"])!=4 or len(fields[b"DATA"])!=24:
                raise ValueError("only simple unlinked references supported")
            base=s.slots.decode(struct.unpack("<I",fields[b"NAME"])[0])
            if base is None or s.types.get(base)!="STAT":raise ValueError("only resolved static references supported")
            old=struct.unpack("<6f",fields[b"DATA"])
            if not all(math.isfinite(v) for v in old) or tuple(math.floor(v/4096) for v in old[:2])!=grid(cells[0]):
                raise ValueError("source position disagrees with cell")
            if not all(math.isfinite(v) and abs(v)<=1e7 for v in (x,y,z)):raise ValueError("invalid destination position")
            data=struct.pack("<6f",x,y,z,*old[3:]);actual=struct.unpack("<6f",data)
            if tuple(math.floor(v/4096) for v in actual[:2])!=grid(dest):raise ValueError("position outside destination cell")
            moved=replace(node,payload=set_field(parts,b"DATA",data))
            remove=(path,);adds[target_parent]=[moved]
            summary={"source_cell":token(s.profile,s.rows[cells[0]]["key"]),"destination_cell":destination,"before":list(old[:3]),"after":list(actual[:3])}
        else:raise ValueError("unsupported operation")
        raw=serialize(s.profile,tree_edit(s.nodes,edits,adds,remove))
        candidate=NativeSession(s.profile,raw,s.slots)
        after=records(candidate)
        if set(after)!=set(before)|({new_key} if new_key else set()) or any(after[k]!=v for k,v in before.items() if k!=changed):
            raise ValueError("unexpected unrelated record changes")
        if operation=="relocate-reference":
            p=candidate.resolve_identity(identity)
            if candidate.node(p[:-1]).header[8:12]!=cell.header[12:16]:raise ValueError("relocation verification failed")
        if len(raw)>8*1024*1024 or self.project.read()["revision"]!=revision:raise ValueError("stale or oversized output")
        proposal=secrets.token_urlsafe(24) if self.enabled else None
        if proposal:self.pending=(proposal,id,name,raw,revision)
        return {"operation":operation,"id":id,"revision":revision,"identity":identity,"summary":summary,
                "sha256":hashlib.sha256(raw).hexdigest(),"proposal_token":proposal,"apply_enabled":self.enabled,"requires_game_testing":True}
