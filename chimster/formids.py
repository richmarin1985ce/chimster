"""Stable, explicit project-local FormID allocation. Never reuse retired IDs."""
from pathlib import Path
import json,re
from .loadorder import plugin_name
KEY=re.compile(r"[A-Za-z0-9_.:/-]{1,200}")
class FormIDs:
    def __init__(self,plugin,previous=None):
        self.plugin=plugin_name(plugin);self.entries={};self.used=set();self.next=0x800;self.active=set()
        if previous is not None:
            if previous.get("schema")!=1 or previous.get("plugin")!=self.plugin:raise ValueError("ledger belongs to another plugin")
            for k,v in previous["entries"].items():
                if not KEY.fullmatch(k) or type(v) is not int or not 0x800<=v<=0xffffff or v in self.used:raise ValueError("invalid ledger entry")
                self.entries[k]=v;self.used.add(v)
            self.next=previous["next"]
            if type(self.next) is not int or not max(self.used,default=0x7ff)<self.next<=0x1000000:raise ValueError("invalid next FormID")
    def get(self,key):
        if not isinstance(key,str) or not KEY.fullmatch(key) or key in self.active:raise ValueError("invalid or duplicate stable record key")
        self.active.add(key)
        if key not in self.entries:
            if self.next>0xffffff:raise ValueError("FormID space exhausted")
            self.entries[key]=self.next;self.next+=1
        return self.entries[key]
    def reserve(self, keys):
        """Allocate new identities deterministically before ordered serialization."""
        keys=list(keys)
        if any(not isinstance(k,str) or not KEY.fullmatch(k) for k in keys) or len(set(keys))!=len(keys):raise ValueError("invalid or duplicate stable record key")
        if any(k in self.active for k in keys):raise ValueError("cannot reserve active keys")
        missing=sorted(set(keys)-self.entries.keys())
        if self.next+len(missing)>0x1000000:raise ValueError("FormID space exhausted")
        for k in missing:
            self.entries[k]=self.next;self.used.add(self.next);self.next+=1
    def snapshot(self):
        return {"schema":1,"plugin":self.plugin,"next":self.next,"entries":dict(sorted(self.entries.items())),"active":sorted(self.active)}
def load(path):
    p=Path(path)
    if p.stat().st_size>32*1024*1024:raise ValueError("ledger too large")
    return json.loads(p.read_text(encoding="utf-8"))
def staged_build(builder,output,ledger_output,previous=None):
    """Builder receives allocator. Keep old ledger untouched; publish new ledger only after validation."""
    p=Path(output);q=Path(ledger_output)
    if p.exists() or p.is_symlink() or q.exists() or q.is_symlink() or p.resolve()==q.resolve():raise ValueError("expected distinct new plugin and ledger")
    ids=FormIDs(p.name,load(previous) if previous else None)
    result=builder(ids)
    created=False
    try:
        with q.open("x",encoding="utf-8") as f:
            created=True;json.dump(ids.snapshot(),f,indent=2)
    except Exception:
        if created:q.unlink(missing_ok=True)
        p.unlink(missing_ok=True);raise
    return {**result,"formid_ledger":str(q),"allocated_ids":len(ids.entries),"inactive_ids":len(ids.entries)-len(ids.active)}
