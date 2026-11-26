"""Versioned declarative plugin manifests; never imports untrusted extension code."""
from pathlib import Path
import json,re

API_VERSION=1
CAPABILITIES={"record-reader","record-writer","asset-export","validator","launcher","localization","packager"}
def load_manifest(path):
    path=Path(path)
    if path.stat().st_size>65536: raise ValueError("manifest too large")
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or data.get("api_version")!=API_VERSION: raise ValueError("unsupported API")
    if not isinstance(data.get("id"),str) or not re.fullmatch(r"[a-z][a-z0-9.-]{0,79}",data["id"]): raise ValueError("invalid extension ID")
    caps=data.get("capabilities")
    if not isinstance(caps,list) or not all(isinstance(c,str) and c in CAPABILITIES for c in caps): raise ValueError("unknown capability")
    if not isinstance(data.get("version"),str) or not data["version"]: raise ValueError("missing version")
    return {"id":data["id"],"version":data["version"],"api_version":API_VERSION,"capabilities":sorted(set(caps)),"execution_enabled":False}
