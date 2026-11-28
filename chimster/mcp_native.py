"""Native record proposals use the existing staged editor."""
import hashlib
import json
import secrets
import tempfile
from pathlib import Path
from .mcp_operations import named_plugin
from .project import identifier

class NativeProposals:
    def __init__(self,project,recovery,enabled=False):
        self.project=project
        self.recovery=recovery
        self.enabled=enabled
        self.pending=None

    def preview(self,id,origin,local_id,field,value_json,revision,plugin_sha256,record_sha256):
        from .record_editor import inspect,edit_typed
        self.pending=None
        m=self.project.read()
        a=m["artifacts"][identifier(id)]
        if m["game"]!="newvegas" or m["revision"]!=revision or a["sha256"]!=plugin_sha256:
            raise ValueError("unsupported game or stale plugin revision")
        if Path(a["filename"]).suffix.lower()!=".esp":
            raise ValueError("only ESP artifacts supported")
        if not 1<=local_id<=0xffffff or len(field)!=4 or not field.isascii() or len(value_json)>8192:
            raise ValueError("invalid edit")
        def reject_constant(value):
            raise ValueError("nonfinite JSON value")
        value=json.loads(value_json,parse_constant=reject_constant)
        with tempfile.TemporaryDirectory(prefix="chimster-native-") as d:
            base=Path(d)/"source";base.mkdir()
            stage=Path(d)/"stage";stage.mkdir()
            source=named_plugin(self.project,id,m,base)
            before=inspect(source,origin,local_id)
            if before["payload_sha256"]!=record_sha256:
                raise ValueError("stale record hash")
            if before["origin"].casefold()!=source.name.casefold():
                raise ValueError("master overrides excluded")
            target=stage/source.name
            report=edit_typed(source,target,origin,local_id,field,value,record_sha256)
            after=inspect(target,origin,local_id)
            if target.stat().st_size>32*1024*1024:
                raise ValueError("staged output exceeds limit")
            raw=target.read_bytes()
        def field_value(record):
            return next(f["value"] for f in record["fields"] if f["tag"]==field and f["writable"])
        before_value,after_value=field_value(before),field_value(after)
        if len(json.dumps([before_value,after_value],ensure_ascii=True,allow_nan=False))>32768:
            raise ValueError("field preview exceeds limit")
        if self.project.read()["revision"]!=revision:
            raise ValueError("project changed while staging")
        token=secrets.token_urlsafe(24) if self.enabled else None
        if token:
            self.pending=(token,id,a["filename"],raw,revision)
        return {"id":id,"revision":revision,"origin":origin,"local_id":local_id,
                "field":field,"before":before_value,"after":after_value,
                "source_sha256":plugin_sha256,"staged_sha256":hashlib.sha256(raw).hexdigest(),
                "untouched_records":report["untouched_records"],"proposal_token":token,
                "apply_enabled":self.enabled,"requires_game_testing":True}

    def apply(self,token):
        if not self.enabled or self.pending is None or not token.isascii() or not secrets.compare_digest(token,self.pending[0]):
            raise ValueError("no matching native proposal")
        _,key,name,raw,revision=self.pending
        self.pending=None
        with tempfile.TemporaryDirectory(prefix="chimster-native-apply-") as d:
            target=Path(d)/name
            target.write_bytes(raw)
            m=self.project.add(key,"plugin",target,revision,replace=True)
        self.recovery.pending=None
        self.recovery.record_commit(revision,m["revision"])
        return {"id":key,"revision":m["revision"],"artifact":m["artifacts"][key],
                "undo_target_revision":revision,"requires_game_testing":True}
