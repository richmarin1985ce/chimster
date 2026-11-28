"""Isolated pure production previews; only parent session can publish."""
import base64
import hashlib
import json
import secrets
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .project import identifier
from .mcp_production import Production,LIMIT

OPERATIONS={"native-build","navmesh","font","fuz","texture-material","mesh-lod",
            "mesh-preview","mesh-model","scene-render","audio-normalize"}
WIRE_LIMIT=24*1024*1024

def worker(project):
    raw=sys.stdin.buffer.read(131073)
    if len(raw)>131072:raise ValueError("worker input exceeds limit")
    args=json.loads(raw)
    if not isinstance(args,dict) or args.get("operation") not in OPERATIONS:
        raise ValueError("unsupported worker operation")
    p=Production(project,None,True)
    preview=p.preview(**args)
    _,revision,outputs=p.pending
    preview.pop("proposal_token",None)
    result={"preview":preview,"outputs":[[k,kind,name,base64.b64encode(data).decode("ascii")] for k,kind,name,data in outputs]}
    raw=json.dumps(result,ensure_ascii=True,allow_nan=False)
    if len(raw)>WIRE_LIMIT:raise ValueError("worker output exceeds limit")
    print(raw)

class ProductionJobs:
    def __init__(self,production):
        self.production=production
        self.pool=ThreadPoolExecutor(max_workers=1)
        self.entry=None

    def start(self,args):
        if self.entry is not None:raise ValueError("collect or discard previous production job")
        if args.get("operation") not in OPERATIONS:raise ValueError("operation not interruptible")
        revision=args["revision"]
        if self.production.project.read()["revision"]!=revision:raise ValueError("stale revision")
        self.production.pending=None
        event=threading.Event()
        data=json.dumps(args,ensure_ascii=True,allow_nan=False).encode("ascii")
        if len(data)>131072:raise ValueError("worker input exceeds limit")
        def run():
            if event.is_set():raise ValueError("cancelled")
            cmd=[sys.executable] if getattr(sys,"frozen",False) else [sys.executable,"-m","chimster"]
            cmd+=["--mcp","--project",str(self.production.project.root),"--production-worker"]
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            deadline=time.monotonic()+180
            try:
                first=True
                while True:
                    if event.is_set() or time.monotonic()>deadline:raise ValueError("cancelled or timed out")
                    try:
                        inp=data if first else None
                        first=False
                        raw,_=proc.communicate(input=inp,timeout=.15)
                        break
                    except subprocess.TimeoutExpired:continue
                if proc.returncode or len(raw)>WIRE_LIMIT or event.is_set():raise ValueError("worker failed")
                return json.loads(raw)
            finally:
                if proc.poll() is None:proc.kill()
                proc.communicate()
        key=secrets.token_hex(16)
        self.entry=(key,revision,event,self.pool.submit(run))
        return {"job_id":key,"revision":revision,"state":"queued"}

    def get(self,key):
        if self.entry is None or self.entry[0]!=key:raise ValueError("unknown production job")
        return self.entry

    def status(self,job_id):
        key,rev,event,f=self.get(job_id)
        state="cancelled" if f.cancelled() or (event.is_set() and f.done()) else "cancelling" if event.is_set() else "failed" if f.done() and f.exception() else "completed" if f.done() else "running" if f.running() else "queued"
        return {"job_id":key,"revision":rev,"state":state}

    def cancel(self,job_id):
        _,_,event,f=self.get(job_id)
        if not f.done():event.set();f.cancel()
        return self.status(job_id)

    def discard(self,job_id):
        _,_,_,f=self.get(job_id)
        if not f.done():raise ValueError("job active")
        self.entry=None
        return {"discarded":job_id}

    def collect(self,job_id):
        status=self.status(job_id)
        if status["state"]!="completed":return status
        _,revision,_,f=self.get(job_id)
        self.entry=None
        p=self.production
        if p.project.read()["revision"]!=revision:raise ValueError("stale production result")
        result=f.result()
        preview=result["preview"]
        outputs=[]
        if not 1<=len(result["outputs"])<=8 or len(preview["outputs"])!=len(result["outputs"]):
            raise ValueError("invalid output bundle")
        for (key,kind,name,encoded),meta in zip(result["outputs"],preview["outputs"]):
            identifier(key)
            if Path(name).name!=name or not name.startswith("generated-") or not name.isascii() or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in name):
                raise ValueError("unsafe output name")
            raw=base64.b64decode(encoded,validate=True)
            if meta!={"id":key,"kind":kind,"filename":name,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}:
                raise ValueError("output mismatch")
            outputs.append((key,kind,name,raw))
        if sum(len(r[3]) for r in outputs)>LIMIT:raise ValueError("output size limit")
        token=secrets.token_urlsafe(24) if p.enabled else None
        p.pending=(token,revision,outputs) if token else None
        preview.update(proposal_token=token,apply_enabled=p.enabled)
        return preview

    def close(self):
        if self.entry:self.entry[2].set()
        self.pool.shutdown(wait=False,cancel_futures=True)
