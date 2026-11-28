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

def native_browse(project,id,offset=0,limit=50,signature="",validate=False):
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
        filename=output_id+".obj"
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
