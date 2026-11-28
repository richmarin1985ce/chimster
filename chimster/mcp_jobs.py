"""Session-local read-only jobs; no arbitrary executable or filesystem access."""
from concurrent.futures import ThreadPoolExecutor
import json
import secrets

class Jobs:
    def __init__(self, project):
        self.project=project
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix="chimster-diagnostics")
        self.entries={}
    def start(self, operation, handler):
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
        return {"job_id":key,"revision":rev,"operation":operation}
    def status(self,job_id):
        op,rev,future=self.entries[job_id]
        state="cancelled" if future.cancelled() else "failed" if future.done() and future.exception() else "completed" if future.done() else "running" if future.running() else "queued"
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
        return {**self.status(job_id),"cancelled_now":f.cancel(),"note":"Only queued work can be cancelled; running validators must finish."}
    def discard(self,job_id):
        if not self.entries[job_id][2].done():
            raise ValueError("job still active")
        del self.entries[job_id]
        return {"discarded":job_id}
    def close(self):
        self.pool.shutdown(wait=False,cancel_futures=True)
