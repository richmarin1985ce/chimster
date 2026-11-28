"""Opt-in client config registration. No client auto-detection or network calls."""
import json
import os
import secrets
import stat
from pathlib import Path
from .project import atomic_json

MAX_CONFIG=1024*1024

def register_config(path, config):
    p=Path(path).expanduser().absolute()
    if not p.parent.is_dir() or p.is_symlink():
        raise ValueError("existing configuration directory and regular file required")
    if p.exists():
        st=p.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_size>MAX_CONFIG:
            raise ValueError("unsupported client configuration")
        original=p.read_bytes()
        data=json.loads(original)
    else:
        original=None
        data={}
    if not isinstance(data,dict):
        raise ValueError("configuration must be a JSON object")
    servers=data.setdefault("mcpServers",{})
    if not isinstance(servers,dict):
        raise ValueError("invalid mcpServers")
    proposed=config["mcpServers"]["chimster"]
    if "chimster" in servers:
        if servers["chimster"]==proposed:
            return {"registered":True,"changed":False,"path":str(p),"backup":None}
        raise ValueError("different Chimster entry already exists; review it manually")
    servers["chimster"]=proposed
    backup=None
    if original is None:
        # Exclusive creation cannot replace another client's newly created file.
        fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(data,f,indent=2,allow_nan=False)
            f.write("\n")
    else:
        if p.is_symlink() or p.read_bytes()!=original:
            raise ValueError("configuration changed; retry after closing client")
        backup=p.with_name(p.name+".chimster-backup-"+secrets.token_hex(8))
        fd=os.open(backup,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,"wb") as f:
            f.write(original)
        if p.is_symlink() or p.read_bytes()!=original:
            raise ValueError("configuration changed; backup retained")
        # Caller must close the client before registering; the preflight
        # comparison does not synchronize with an uncooperative writer.
        atomic_json(p,data)
    return {"registered":True,"changed":True,"path":str(p),"backup":str(backup) if backup else None}
