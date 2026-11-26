"""Resolve explicit FNV dependencies using master-origin identities, not load-order IDs."""
from pathlib import Path
from .fnv_records import scan
from .loadorder import plugin_name,fingerprint
import struct
from .fnv_patch import sub
class Bindings:
    def __init__(self,paths,output):
        self.paths=[Path(p).resolve(strict=True) for p in paths]
        self.names=[plugin_name(p.name) for p in self.paths]
        if len(self.names)>253 or len(set(self.names))!=len(self.names) or plugin_name(Path(output).name) in self.names:raise ValueError("invalid dependency list")
        self.hashes=[fingerprint(p) for p in self.paths];self.records={}
        for i,p in enumerate(self.paths):
            r=scan(p)
            if any(plugin_name(m) not in self.names[:i] for m in r["masters"]):raise ValueError("missing or out-of-order dependency")
            for rec in r["records"]:
                self.records[(rec["origin"],rec["local_id"])]=rec
        self.check()
    @property
    def slot(self):return len(self.names)<<24
    def resolve(self,ref,kinds):
        if not isinstance(ref,dict) or set(ref)!={"plugin","id"} or type(ref["id"]) is not int or not 0<ref["id"]<=0xffffff:raise ValueError("use plugin origin and local ID")
        key=(plugin_name(ref["plugin"]),ref["id"]);r=self.records.get(key)
        if key[0] not in self.names or r is None or r["flags"]&0x20 or r["signature"] not in kinds:raise ValueError("missing, deleted or wrong-type reference: "+str(key))
        return (self.names.index(key[0])<<24)|key[1]
    def header(self):
        return b"".join(sub(b"MAST",p.name.encode("cp1252")+b"\0")+sub(b"DATA",struct.pack("<Q",p.stat().st_size)) for p in self.paths)
    def check(self):
        if self.hashes!=[fingerprint(p) for p in self.paths]:raise ValueError("dependencies changed")
