"""Opt-in local process SDK, JSON request/response protocol.

Trust means arbitrary code execution as the current OS user. This is NOT a sandbox.
No automatic execution, shell invocation, network fetching or imported Python code.
"""
from pathlib import Path
import json,os,subprocess,tempfile,re
from .sdk import load_manifest
from .project import digest,atomic_json,read_json
def approve(manifest,executable,trust_file):
    m=Path(manifest).resolve(strict=True);e=Path(executable).resolve(strict=True)
    info=load_manifest(m)
    if not e.is_file() or os.name!="nt" and not os.access(e,os.X_OK):raise ValueError("executable required")
    data={"schema":1,"id":info["id"],"manifest":str(m),"manifest_hash":digest(m),"executable":str(e),"executable_hash":digest(e)}
    q=Path(trust_file)
    if q.exists() or q.is_symlink():raise ValueError("new approval file required")
    with q.open("x",encoding="utf-8") as f:json.dump(data,f,indent=2)
    return data
def invoke(trust_file,capability,payload,*,timeout=30,execute=False):
    if not execute:raise ValueError("explicit execution approval required; local extension code is not sandboxed")
    if type(timeout) is not int or not 1<=timeout<=120:raise ValueError("invalid timeout")
    trust=read_json(Path(trust_file),65536)
    if trust.get("schema")!=1:raise ValueError("unknown approval schema")
    m=Path(trust["manifest"]);e=Path(trust["executable"])
    if digest(m)!=trust["manifest_hash"] or digest(e)!=trust["executable_hash"]:raise ValueError("extension changed; reapproval required")
    info=load_manifest(m)
    if info["id"]!=trust["id"] or capability not in info["capabilities"]:raise ValueError("unapproved capability")
    request={"api_version":1,"capability":capability,"payload":payload}
    raw=json.dumps(request,allow_nan=False).encode()
    if len(raw)>1024*1024:raise ValueError("request exceeds limit")
    with tempfile.TemporaryDirectory(prefix="chimster-extension-") as d:
        p=Path(d);(p/"request.json").write_bytes(raw)
        # No project cwd or inherited API tokens by default. An approved program
        # still has the same OS permissions as the user and can access files/network.
        env={k:v for k,v in os.environ.items() if k in {"PATH","SystemRoot","WINDIR","TEMP","TMP","TMPDIR","LANG","LC_ALL"}}
        with (p/"stdout").open("wb") as out,(p/"stderr").open("wb") as err:
            cp=subprocess.run([str(e),str(p/"request.json"),str(p/"response.json")],cwd=d,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=timeout,shell=False)
        if cp.returncode:raise ValueError("extension failed with exit code "+str(cp.returncode))
        response=read_json(p/"response.json",4*1024*1024)
        if response.get("api_version")!=1 or type(response.get("ok")) is not bool or set(response)-{"api_version","ok","result","error"}:raise ValueError("invalid extension response")
        if not response["ok"]:raise ValueError("extension reported failure")
        if "result" not in response:raise ValueError("missing extension result")
        return {"extension":info["id"],"capability":capability,"result":response["result"],"scope":"trusted local executable; not sandboxed or automatically applied"}
