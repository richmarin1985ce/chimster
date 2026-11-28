"""Local editor presence, not an IPC endpoint or an authorization grant."""
import os
import stat
import time
import uuid
from pathlib import Path
from .project import Project, atomic_json, read_json

TTL = 15
def directory(root=None):
    p = Path(root) if root is not None else Path.home()/".chimster-editor-instances"
    p.mkdir(mode=0o700, exist_ok=True)
    st = p.lstat()
    if not stat.S_ISDIR(st.st_mode) or p.is_symlink():
        raise ValueError("unsafe presence directory")
    if os.name == "posix" and (st.st_uid != os.getuid() or st.st_mode & 0o077):
        raise ValueError("presence directory must be private")
    return p

class Presence:
    def __init__(self, root=None):
        self.directory = directory(root)
        self.id = uuid.uuid4().hex
        self.path = self.directory/(self.id+".json")
    def publish(self, project, selected=None):
        m = project.read()
        atomic_json(self.path, {"schema":1,"id":self.id,"heartbeat":time.time(),
                   "project":str(project.root),"revision":m["revision"],
                   "selected":selected if selected in m["artifacts"] else None})
    def close(self):
        self.path.unlink(missing_ok=True)

def discover(root=None):
    result=[]
    now=time.time()
    for p in sorted(directory(root).glob("*.json"))[:256]:
        try:
            if p.is_symlink() or not p.is_file():
                continue
            st=p.stat()
            if os.name=="posix" and (st.st_uid!=os.getuid() or st.st_mode&0o077):
                continue
            m=read_json(p,8192)
            if m["schema"]!=1 or m["id"]+".json"!=p.name or uuid.UUID(hex=m["id"]).hex!=m["id"]:
                continue
            if not 0<=now-m["heartbeat"]<=TTL:
                continue
            project=Project(m["project"])
            data=project.read()
            result.append({"id":m["id"],"project":str(project.root),"name":data["name"],
                           "game":data["game"],"revision":data["revision"],
                           "selected":m["selected"] if m["selected"] in data["artifacts"] else None})
        except (OSError,ValueError,KeyError,TypeError,AttributeError):
            continue
    return result

def select(instance, root=None):
    for item in discover(root):
        if item["id"]==instance:
            return Project(item["project"])
    raise ValueError("active editor instance not found")
