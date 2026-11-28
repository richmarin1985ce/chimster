"""Bounded native browsing and intermediate asset proposals."""
import hashlib
import json
import secrets
import tempfile
from pathlib import Path
from .mcp_operations import artifact_input
from .project import identifier

def native_profile(game):
    from .native_profiles import canonical_profile,active_profiles
    p=canonical_profile("morrowind" if game=="openmw" else game)
    if p not in active_profiles():raise ValueError("native profile deferred")
    return p

def native_session(project,id):
    from .native_parser import parse,subrecords
    from .native_editor import NativeSession
    from .record_graph import Slots
    m,a,p=artifact_input(project,id,8*1024*1024)
    if a["kind"]!="plugin":raise ValueError("expected plugin artifact")
    profile=native_profile(m["game"])
    raw=p.read_bytes()
    nodes=parse(profile,raw)
    expected=b"TES3" if profile=="morrowind" else b"TES4"
    if not nodes or nodes[0].signature!=expected:raise ValueError("wrong plugin header")
    masters=[v.rstrip(b"\0").decode("cp1252") for tag,v in subrecords(profile,nodes[0]) if tag==b"MAST"]
    session=NativeSession(profile,raw,None if profile=="morrowind" else Slots(a["filename"],masters))
    return m,a,session,masters

def native_browse(project,id,offset=0,limit=50,signature="",validate=False):
    m,a,session,masters=native_session(project,id)
    profile=session.profile
    if signature and (len(signature)!=4 or not signature.isascii()):raise ValueError("invalid signature")
    paths=[path for path in session.rows if not signature or session.node(path).signature.decode("ascii")==signature]
    rows=[]
    for path in paths[offset:offset+limit]:
        row=session.rows[path]
        key=row["key"]
        token=session.identity_token(path) if key is not None else None
        rows.append({"path":list(path),"signature":session.node(path).signature.decode("ascii"),
                     "identity":token if token is None or len(token)<=2048 else None,
                     "field_count":len(row["parts"]),"known_references":len(row["edges"]),
                     "opaque_fields":len(row["opaque"])})
    result={"id":id,"revision":m["revision"],"profile":profile,"masters":masters,
            "records":rows,"total":len(paths),"next_offset":offset+limit if offset+limit<len(paths) else None,
            "retail_verified":False}
    if validate:
        report=session.validation_summary()
        result["validation"]={k:report[k] for k in ("records","counts","severity_counts","complete")}
    return result

class MeshProposals:
    def __init__(self,project,recovery,enabled=False):
        self.project=project
        self.recovery=recovery
        self.enabled=enabled
        self.pending=None

    def preview(self,id,output_id,scale_percent,yaw_degrees,ground,revision,sha256):
        from .scene import load_obj
        from .asset_forge import Session
        self.pending=None
        identifier(output_id)
        m,a,p=artifact_input(self.project,id,8*1024*1024)
        if m["revision"]!=revision or a["sha256"]!=sha256 or a["kind"]!="mesh" or Path(a["filename"]).suffix.lower()!=".obj":
            raise ValueError("stale or unsupported mesh")
        if any(k.casefold()==output_id.casefold() for k in m["artifacts"]):
            raise ValueError("output already exists")
        if not 1<=scale_percent<=1000 or not -360<=yaw_degrees<=360 or type(ground) is not bool:
            raise ValueError("invalid transform")
        s=Session(load_obj(p))
        before=s.report()
        s.transform(scale=scale_percent/100,yaw=yaw_degrees,ground=ground)
        after=s.report()
        filename="generated-"+output_id+".obj"
        with tempfile.TemporaryDirectory(prefix="chimster-mesh-") as d:
            path=Path(d)/filename
            s.export_obj(path)
            if path.stat().st_size>16*1024*1024:raise ValueError("output exceeds limit")
            Session(load_obj(path))
            raw=path.read_bytes()
        if self.project.read()["revision"]!=revision:raise ValueError("stale revision")
        token=secrets.token_urlsafe(24) if self.enabled else None
        if token:self.pending=(token,output_id,filename,raw,revision)
        return {"id":id,"output_id":output_id,"revision":revision,"before":before,"after":after,
                "sha256":hashlib.sha256(raw).hexdigest(),"proposal_token":token,"apply_enabled":self.enabled,
                "format":"intermediate OBJ; native export not performed"}

    def apply(self,token):
        if not self.enabled or self.pending is None or not token.isascii() or not secrets.compare_digest(token,self.pending[0]):
            raise ValueError("invalid mesh proposal")
        _,key,filename,raw,revision=self.pending
        self.pending=None
        with tempfile.TemporaryDirectory(prefix="chimster-mesh-apply-") as d:
            p=Path(d)/filename
            p.write_bytes(raw)
            m=self.project.add(key,"mesh",p,revision,replace=False)
        self.recovery.pending=None
        self.recovery.record_commit(revision,m["revision"])
        return {"id":key,"revision":m["revision"],"artifact":m["artifacts"][key],"undo_target_revision":revision}

def native_detail(project,id,identity,offset=0,limit=50):
    from .native_identity import token
    m,a,s,_=native_session(project,id)
    path=s.resolve_identity(identity)
    row=s.rows[path]
    edges={}
    for i,o,target,kinds in row["edges"]:
        edges.setdefault(i,[]).append({"offset":o,"identity":token(s.profile,target),
                                      "expected_types":sorted(kinds)})
    fields=[{"index":i,"tag":tag.decode("ascii",errors="replace"),"size":len(raw),
             "hex_preview":raw[:32].hex(),"opaque":i in row["opaque"],"references":edges.get(i,[])}
            for i,(tag,raw) in enumerate(row["parts"]) if offset<=i<offset+limit]
    return {"id":id,"revision":m["revision"],"sha256":a["sha256"],"identity":identity,
            "signature":s.node(path).signature.decode("ascii"),"fields":fields,
            "total":len(row["parts"]),"next_offset":offset+limit if offset+limit<len(row["parts"]) else None}

REFERENCE_PROFILES={"oblivion","fallout3","new-vegas","skyrim","skyrim-se","fallout4"}

class ReferenceProposals:
    """Owned full-slot ESP records, known fields, same-plugin targets only."""
    def __init__(self,project,recovery,enabled=False):
        self.project=project
        self.recovery=recovery
        self.enabled=enabled
        self.pending=None

    def preview(self,id,identity,index,offset,expected_identity,target_identity,revision,sha256):
        import struct
        from .native_identity import parse_token
        from .loadorder import plugin_name
        self.pending=None
        m,a,s,masters=native_session(self.project,id)
        if s.profile not in REFERENCE_PROFILES or m["revision"]!=revision or a["sha256"]!=sha256:
            raise ValueError("unsupported profile or stale revision")
        name=a["filename"]
        if not name.isascii() or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- " for c in name) or name.split(".")[0].strip().upper() in {"CON","PRN","AUX","NUL",*[f"COM{i}" for i in range(1,10)],*[f"LPT{i}" for i in range(1,10)]}:
            raise ValueError("unsafe plugin filename")
        if Path(name).suffix.lower()!=".esp" or struct.unpack_from("<I",s.nodes[0].header,8)[0]&0x200:
            raise ValueError("full-slot ESP required")
        own=plugin_name(a["filename"])
        path=s.resolve_identity(identity)
        key=s.rows[path]["key"]
        expected=parse_token(expected_identity,s.profile)[1] if expected_identity else None
        target=parse_token(target_identity,s.profile)[1]
        if key.origin!=own or target.origin!=own:
            raise ValueError("only same-plugin owned records and targets")
        s.resolve_identity(target_identity)
        before=s.node(path)
        originals={p:(s.node(p).header,s.node(p).payload) for p in s.rows if p!=path}
        s.apply(s.revision,[(identity,index,expected,target,offset)])
        if set(s.rows)!=(set(originals)|{path}) or any((s.node(p).header,s.node(p).payload)!=value for p,value in originals.items()):
            raise ValueError("unexpected changes to unrelated records")
        raw=s.data
        if len(raw)>8*1024*1024 or self.project.read()["revision"]!=revision:
            raise ValueError("stale or oversized output")
        token=secrets.token_urlsafe(24) if self.enabled else None
        if token:self.pending=(token,id,a["filename"],raw,revision)
        return {"id":id,"revision":revision,"identity":identity,"field_index":index,"field_offset":offset,
                "before":expected_identity or None,"after":target_identity,"untouched_records":len(originals),
                "sha256":hashlib.sha256(raw).hexdigest(),"proposal_token":token,"apply_enabled":self.enabled,
                "requires_game_testing":True}

    def apply(self,token):
        if not self.enabled or self.pending is None or not token.isascii() or not secrets.compare_digest(token,self.pending[0]):
            raise ValueError("invalid reference proposal")
        _,key,name,raw,revision=self.pending
        self.pending=None
        with tempfile.TemporaryDirectory(prefix="chimster-reference-") as d:
            p=Path(d)/name;p.write_bytes(raw)
            m=self.project.add(key,"plugin",p,revision,replace=True)
        self.recovery.pending=None
        self.recovery.record_commit(revision,m["revision"])
        return {"id":key,"revision":m["revision"],"artifact":m["artifacts"][key],"requires_game_testing":True}
