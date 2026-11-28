"""Session-local read-only jobs; no arbitrary executable or filesystem access."""
from concurrent.futures import ThreadPoolExecutor
import json
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

class Jobs:
    def __init__(self, project):
        self.project=project
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="chimster-diagnostics")
        self.entries={}
        self.interruptions={}
    def start(self, operation, handler, cancel_event=None):
        if len(self.entries)>=8:
            raise ValueError("job limit; discard completed jobs first")
        rev=self.project.read()["revision"]
        def run():
            if self.project.read()["revision"]!=rev:
                raise ValueError("stale job revision")
            result=handler()
            if self.project.read()["revision"]!=rev:
                raise ValueError("project changed during job")
            # Retain only serializable, bounded results.
            if len(json.dumps(result,ensure_ascii=True,allow_nan=False))>512*1024:
                raise ValueError("job result exceeds limit")
            return result
        key=secrets.token_hex(16)
        self.entries[key]=(operation,rev,self.pool.submit(run))
        if cancel_event is not None:self.interruptions[key]=cancel_event
        return {"job_id":key,"revision":rev,"operation":operation}
    def status(self,job_id):
        op,rev,future=self.entries[job_id]
        interrupted=self.interruptions.get(job_id)
        state="cancelled" if future.cancelled() or (interrupted and interrupted.is_set() and future.done()) else "cancelling" if interrupted and interrupted.is_set() else "failed" if future.done() and future.exception() else "completed" if future.done() else "running" if future.running() else "queued"
        return {"job_id":job_id,"operation":op,"revision":rev,"state":state}
    def result(self,job_id):
        row=self.status(job_id)
        if row["state"]=="completed":
            row["result"]=self.entries[job_id][2].result()
        elif row["state"]=="failed":
            row["error"]="Diagnostic failed, exceeded limits, or project changed."
        return row
    def cancel(self,job_id):
        f=self.entries[job_id][2]
        cancelled=f.cancel()
        event=self.interruptions.get(job_id)
        if not cancelled and not f.done() and event is not None:
            event.set();cancelled=True
        return {**self.status(job_id),"cancelled_now":cancelled,"note":"Isolated diagnostics are interruptible; legacy in-process callbacks can only be cancelled while queued."}
    def discard(self,job_id):
        if not self.entries[job_id][2].done():
            raise ValueError("job still active")
        del self.entries[job_id]
        self.interruptions.pop(job_id,None)
        return {"discarded":job_id}
    def close(self):
        for event in self.interruptions.values():event.set()
        self.pool.shutdown(wait=False,cancel_futures=True)

    def start_isolated(self,operation,id):
        event=threading.Event()
        def run():
            if event.is_set():raise ValueError("cancelled")
            command=[sys.executable] if getattr(sys,"frozen",False) else [sys.executable,"-m","chimster"]
            command+=["--mcp","--project",str(self.project.root),"--diagnostic-worker",operation,id]
            proc=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            deadline=time.monotonic()+120
            try:
                while True:
                    if event.is_set() or time.monotonic()>deadline:
                        raise ValueError("cancelled or timed out")
                    try:
                        raw,_=proc.communicate(timeout=.15)
                        break
                    except subprocess.TimeoutExpired:continue
                if proc.returncode or len(raw)>512*1024 or event.is_set():
                    raise ValueError("diagnostic worker failed")
                return json.loads(raw)
            finally:
                if proc.poll() is None:proc.kill()
                proc.communicate()
        return self.start(operation,run,event)

def worker(project,operation,id):
    from .mcp_operations import diagnose,inspect_asset,inspect_plugin_artifact
    from .mcp_extended import native_browse
    from .project import identifier
    identifier(id)
    if operation in ("quest","interior","papyrus","legacy-script","navmesh-registration"):
        result=diagnose(project,id,operation)
    elif operation in ("audio","mesh","scene","font"):
        result=inspect_asset(project,id,operation)
    elif operation=="native":result=native_browse(project,id,validate=True)
    elif operation=="plugin":result=inspect_plugin_artifact(project,id)
    else:raise ValueError("unsupported diagnostic")
    raw=json.dumps(result,ensure_ascii=True,allow_nan=False)
    if len(raw)>512*1024:raise ValueError("diagnostic result limit")
    print(raw)
