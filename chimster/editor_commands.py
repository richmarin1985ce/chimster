"""Same-user dashboard selection/refresh only; no arbitrary GUI or file actions."""
import os
import re
import stat
import time
import uuid
from .editor_presence import directory, discover
from .project import atomic_json, read_json, identifier

ID=re.compile(r"[0-9a-f]{32}")
TTL=15
VIEW_ACTIONS=("viewport-fit","viewport-left","viewport-right","viewport-up","viewport-down","viewport-zoom-in","viewport-zoom-out","viewport-show")

def mailbox(instance,root=None,create=False):
    if not isinstance(instance,str) or not ID.fullmatch(instance):
        raise ValueError("invalid instance")
    p=directory(root)/(instance+".commands")
    if create:p.mkdir(mode=0o700,exist_ok=True)
    st=p.lstat()
    if not stat.S_ISDIR(st.st_mode) or p.is_symlink():
        raise ValueError("unsafe mailbox")
    if os.name=="posix" and (st.st_uid!=os.getuid() or st.st_mode&0o077):
        raise ValueError("mailbox must be private")
    return p

def submit(project,instance,action,revision,artifact=None,root=None):
    m=project.read()
    if m["revision"]!=revision or action not in ("refresh","select")+VIEW_ACTIONS:
        raise ValueError("stale revision or unsupported action")
    if action=="select":
        identifier(artifact)
        if artifact not in m["artifacts"]:raise ValueError("artifact unavailable")
    elif artifact is not None:raise ValueError("unexpected artifact")
    if not any(r["id"]==instance and r["project"]==str(project.root) for r in discover(root)):
        raise ValueError("instance unavailable or different project")
    box=mailbox(instance,root)
    if len(list(box.glob("*.json")))>=16:raise ValueError("mailbox full")
    key=uuid.uuid4().hex
    atomic_json(box/(key+".json"),{"schema":1,"id":key,"project":str(project.root),
                "revision":revision,"action":action,"artifact":artifact,"created":time.time()})
    return {"request_id":key,"state":"queued","note":"Check editor context for selection; execution not yet confirmed."}

def consume(project,instance,callback,root=None):
    box=mailbox(instance,root)
    for p in sorted(box.glob("*.json"))[:16]:
        try:
            st=p.lstat()
            if not stat.S_ISREG(st.st_mode) or p.is_symlink():continue
            if os.name=="posix" and (st.st_uid!=os.getuid() or st.st_mode&0o077):continue
            r=read_json(p,8192)
            m=project.read()
            if r["schema"]!=1 or r["id"]+".json"!=p.name or not ID.fullmatch(r["id"]):continue
            if not 0<=time.time()-r["created"]<=TTL or r["project"]!=str(project.root) or r["revision"]!=m["revision"]:continue
            if r["action"]=="refresh" and r["artifact"] is None:callback("refresh",None)
            elif r["action"]=="select" and identifier(r["artifact"]) in m["artifacts"]:callback("select",r["artifact"])
            elif r["action"] in VIEW_ACTIONS and r["artifact"] is None:callback(r["action"],None)
        except (OSError,ValueError,KeyError,TypeError,AttributeError):pass
        finally:p.unlink(missing_ok=True)
