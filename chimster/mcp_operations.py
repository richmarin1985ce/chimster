"""Project-scoped MCP operations. No agent-supplied filesystem paths."""
import hashlib
import json
import secrets
import tempfile
from pathlib import Path
from .project import identifier, KINDS, read_json

MAX_TEXT = 128 * 1024
MAX_DIAGNOSTIC = 2 * 1024 * 1024

def artifact_input(project, key, limit):
    m = project.read()
    a = m["artifacts"][identifier(key)]
    if a["size"] > limit:
        raise ValueError("artifact exceeds input limit")
    return m, a, project._object(a)

def read_text(project, id):
    m, a, p = artifact_input(project, id, MAX_TEXT)
    return {"id": id, "revision": m["revision"], "sha256": a["sha256"],
            "text": p.read_text(encoding="utf-8-sig"), "untrusted_content": True}

def diagnose(project, id, operation):
    m, a, p = artifact_input(project, id, MAX_DIAGNOSTIC)
    if operation == "quest":
        from .quest_editor import validate
        result = validate(read_json(p, MAX_DIAGNOSTIC))
    elif operation == "interior":
        from .interior_layout import validate
        result = validate(read_json(p, MAX_DIAGNOSTIC))
    elif operation == "papyrus":
        from .script_lint import check
        result = check(p.read_text(encoding="utf-8-sig"))
    elif operation == "legacy-script":
        from .legacy_compile import lint
        result = lint(p.read_text(encoding="utf-8-sig"), m["game"])
    elif operation == "navmesh-registration":
        from .fnv_navmesh_review import registration_manifest
        result = registration_manifest(read_json(p, MAX_DIAGNOSTIC)["meshes"])
    else:
        raise ValueError("unknown diagnostic")
    return {"id": id, "revision": m["revision"], "operation": operation,
            "result": result}

class CreationSession:
    """A single pending create-only proposal; revision-checked and reversible.

    The host must explicitly enable creation before launching the server.
    The token binds the exact proposal, not human approval.
    """
    def __init__(self, project, enabled=False):
        self.project = project
        self.enabled = enabled
        self.pending = None

    def preview(self, id, kind, filename, text, revision):
        identifier(id)
        if kind not in KINDS or not isinstance(filename, str):
            raise ValueError("invalid artifact")
        if not filename or len(filename) > 120 or filename in (".", "..") or filename.endswith((".", " ")) or any(c in filename for c in "\\/:") or any(ord(c)<32 for c in filename):
            raise ValueError("invalid filename")
        # Conservative cross-platform names, avoid Windows device filenames.
        if not filename.isascii() or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- " for c in filename):
            raise ValueError("invalid filename")
        if filename.split(".")[0].strip().upper() in {"CON","PRN","AUX","NUL",*[f"COM{i}" for i in range(1,10)],*[f"LPT{i}" for i in range(1,10)]}:
            raise ValueError("reserved filename")
        raw = text.encode("utf-8")
        if len(raw) > MAX_TEXT:
            raise ValueError("text exceeds limit")
        m = self.project.read()
        if m["revision"] != revision or any(k.casefold()==id.casefold() for k in m["artifacts"]):
            raise ValueError("stale revision or artifact already exists")
        token = secrets.token_urlsafe(24) if self.enabled else None
        self.pending = (token, id, kind, filename, raw, revision) if self.enabled else None
        return {"operation":"create", "id":id, "kind":kind, "filename":filename,
                "bytes":len(raw), "sha256":hashlib.sha256(raw).hexdigest(),
                "revision":revision, "apply_enabled":self.enabled, "proposal_token":token}

    def apply(self, token):
        if not self.enabled or self.pending is None or not secrets.compare_digest(token, self.pending[0]):
            raise ValueError("no matching proposal")
        _, key, kind, filename, raw, revision = self.pending
        self.pending = None
        with tempfile.TemporaryDirectory(prefix="chimster-mcp-") as d:
            p = Path(d)/filename
            p.write_bytes(raw)
            m = self.project.add(key, kind, p, revision, replace=False)
        return {"id":key, "revision":m["revision"], "artifact":m["artifacts"][key],
                "undo_target_revision":revision}

def inspect_plugin_artifact(project, id):
    from .core import inspect_plugin
    m, a, p = artifact_input(project, id, 32 * 1024 * 1024)
    if a["kind"] != "plugin":
        raise ValueError("expected plugin artifact")
    return {"id":id, "revision":m["revision"], "report":inspect_plugin(p,m["game"],limit=250000)}

def named_plugin(project, id, manifest, folder):
    """Reconstitute the original filename for FNV identity resolution.
    Never pass hash-named object files to a name-sensitive native parser.
    """
    import shutil
    a = manifest["artifacts"][identifier(id)]
    if a["kind"] != "plugin" or a["size"] > 32 * 1024 * 1024:
        raise ValueError("expected bounded plugin artifact")
    name = a["filename"]
    if Path(name).suffix.lower() not in {".esp",".esm",".esl"}:
        raise ValueError("invalid plugin filename")
    if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- " for c in name):
        raise ValueError("unsafe plugin filename")
    if name.split(".")[0].strip().upper() in {"CON","PRN","AUX","NUL",*[f"COM{i}" for i in range(1,10)],*[f"LPT{i}" for i in range(1,10)]}:
        raise ValueError("reserved filename")
    source = project._object(a)
    target = Path(folder)/name
    if any(p.name.casefold()==name.casefold() for p in Path(folder).iterdir()):
        raise ValueError("duplicate plugin filename")
    with target.open("xb") as f, source.open("rb") as src:
        shutil.copyfileobj(src,f)
    from .project import digest
    if digest(target)!=a["sha256"]:
        raise ValueError("artifact changed while staging")
    return target

def inspect_record(project, id, origin, local_id):
    from .record_editor import inspect
    m = project.read()
    if m["game"] != "newvegas":
        raise ValueError("FNV record inspection only")
    if not 1 <= local_id <= 0xffffff:
        raise ValueError("invalid local FormID")
    with tempfile.TemporaryDirectory(prefix="chimster-inspect-") as d:
        p = named_plugin(project,id,m,d)
        result = inspect(p,origin,local_id)
    return {"id":id,"revision":m["revision"],"record":result}

def check_world(project, ids, quest_links=False, navmesh=False):
    from .world_validator import validate
    m = project.read()
    if m["game"] != "newvegas" or not 1 <= len(ids) <= 8:
        raise ValueError("FNV world validation only; 1–8 ordered plugins")
    if len(set(k.casefold() for k in ids)) != len(ids):
        raise ValueError("duplicate artifact IDs")
    if sum(m["artifacts"][identifier(k)]["size"] for k in ids)>64*1024*1024:
        raise ValueError("aggregate plugin size limit")
    with tempfile.TemporaryDirectory(prefix="chimster-world-") as d:
        paths = [named_plugin(project,k,m,d) for k in ids]
        result = validate(paths,max_records=250000,max_issues=250,
                          quest_links=quest_links,navmesh=navmesh)
    return {"revision":m["revision"],"artifact_ids":ids,"report":result}

def revision_diff(project, target, offset=0, limit=50):
    current = project.read()
    if type(target) is not int or not 0<=target<=current["revision"]:
        raise ValueError("invalid revision")
    previous = project.validate(read_json(project.meta/"revisions"/f"{target}.json"))
    if previous["revision"]!=target or any(previous[k]!=current[k] for k in ("name","game")):
        raise ValueError("invalid snapshot identity")
    old,new=previous["artifacts"],current["artifacts"]
    keys=[k for k in sorted(set(old)|set(new)) if old.get(k)!=new.get(k)]
    rows=[{"id":k,"change":"added" if k not in old else "removed" if k not in new else "modified",
           "before":old.get(k),"after":new.get(k)} for k in keys[offset:offset+limit]]
    return {"from_revision":target,"to_revision":current["revision"],"changes":rows,
            "total":len(keys),"next_offset":offset+limit if offset+limit<len(keys) else None}
