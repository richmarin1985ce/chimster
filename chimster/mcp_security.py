"""Local security records. Same-user OS isolation is the trust boundary."""
import hashlib
import json
import os
import re
import secrets
import stat
import time
from pathlib import Path
from .project import atomic_json,read_json

TTL=300
ID=re.compile(r"[0-9a-f]{32}")

def private_dir(project,name):
    p=project.meta/name
    p.mkdir(mode=0o700,exist_ok=True)
    s=p.lstat()
    if not stat.S_ISDIR(s.st_mode) or p.is_symlink():
        raise ValueError("unsafe security directory")
    if os.name=="posix" and (s.st_uid!=os.getuid() or s.st_mode&0o077):
        raise ValueError("security directory must be private")
    return p

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def audit(project,session,tool,outcome,revision,call_id):
    folder=private_dir(project,"mcp-audit")
    # One exclusive, durable file per event. No arguments, tokens or content.
    row={"schema":1,"time":time.time(),"session":session,"tool":tool,
         "outcome":outcome,"revision":revision,"call_id":call_id}
    p=folder/(secrets.token_hex(16)+".json")
    fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,"w",encoding="utf-8") as f:
        json.dump(row,f,sort_keys=True,allow_nan=False)
        f.write("\n");f.flush();os.fsync(f.fileno())

def request_path(project,key):
    if not isinstance(key,str) or not ID.fullmatch(key):raise ValueError("invalid request ID")
    return private_dir(project,"mcp-approvals")/(key+".json")

def load_request(project,key):
    p=request_path(project,key)
    row=read_json(p,65536)
    if row["id"]!=key or not 0<=time.time()-row["created"]<=TTL:
        raise ValueError("expired approval")
    if row["revision"]!=project.read()["revision"]:
        raise ValueError("project changed")
    return p,row

def review(project,key):
    import sys
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise ValueError("approval requires an interactive local terminal")
    p,row=load_request(project,key)
    if row["decision"]!="pending":raise ValueError("already reviewed")
    print(json.dumps({k:row[k] for k in ("tool","revision","summary","id")},indent=2,ensure_ascii=True))
    answer=input("Type APPROVE to authorize this exact operation, or anything else to deny: ")
    p,latest=load_request(project,key)
    if latest!=row:raise ValueError("approval changed during review")
    row["decision"]="approved" if answer=="APPROVE" else "denied"
    atomic_json(p,row)
    return {"id":key,"decision":row["decision"]}

class Gate:
    def __init__(self,project):
        self.project=project
        self.session=secrets.token_hex(16)
        self.pending={}

    def check(self,tool,args,summary,revision):
        binding=fingerprint([self.session,tool,args,summary,revision])
        # Reuse the exact pending request; a different call cannot inherit consent.
        for old,key in list(self.pending.items()):
            try:load_request(self.project,key)
            except (OSError,ValueError,KeyError,TypeError):
                self.pending.pop(old,None)
                request_path(self.project,key).unlink(missing_ok=True)
        key=self.pending.get(binding)
        if key:
            p,row=load_request(self.project,key)
            if row["binding"]!=binding or row["session"]!=self.session:raise ValueError("approval binding mismatch")
            if row["decision"]=="approved":
                p.unlink();self.pending.pop(binding,None)
                return None
            if row["decision"]=="denied":
                p.unlink();self.pending.pop(binding,None)
                raise ValueError("operation denied")
            return key
        if len(self.pending)>=8:raise ValueError("approval queue full")
        key=secrets.token_hex(16)
        row={"id":key,"session":self.session,"binding":binding,"tool":tool,"revision":revision,
             "summary":summary,"created":time.time(),"decision":"pending"}
        if len(json.dumps(row,ensure_ascii=True))>60000:raise ValueError("approval summary too large")
        atomic_json(request_path(self.project,key),row)
        self.pending[binding]=key
        return key
