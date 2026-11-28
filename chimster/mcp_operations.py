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
