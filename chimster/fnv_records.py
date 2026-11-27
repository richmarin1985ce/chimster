"""MIT experimental FNV full-plugin record index, not a semantic xEdit replacement."""
import struct,sqlite3,json,hashlib
from pathlib import Path
from .loadorder import plugin_name,dependency_order,fingerprint
HEADER=struct.Struct("<4sIIIIHH")
MAX_RECORD=64*1024*1024

def subs(data):
    p=0
    while p<len(data):
        if len(data)-p<6:raise ValueError("truncated subrecord")
        k,n=struct.unpack_from("<4sH",data,p);p+=6
        if k==b"XXXX":
            if n!=4 or p+10>len(data):raise ValueError("bad XXXX")
            n=struct.unpack_from("<I",data,p)[0];p+=4
            k,_=struct.unpack_from("<4sH",data,p);p+=6
            if k==b"XXXX":raise ValueError("nested XXXX")
        if p+n>len(data):raise ValueError("bad subrecord length")
        yield k,data[p:p+n];p+=n

def text(raw):
    if not raw or raw[-1:]!=b"\0" or b"\0" in raw[:-1]:raise ValueError("invalid cstring")
    return raw[:-1].decode("cp1252")

def scan(path):
    path=Path(path);size=path.stat().st_size
    with path.open("rb") as f:
        def read(n):
            b=f.read(n)
            if len(b)!=n:raise ValueError("truncated record")
            return b
        h=read(24);sig,n,flags,form,vc,ver,unknown=HEADER.unpack(h)
        if sig!=b"TES4" or form or flags&~1 or n>MAX_RECORD or 24+n>size:raise ValueError("unsupported FNV header")
        parts=list(subs(read(n)))
        master=[text(v) for k,v in parts if k==b"MAST"]
        headers=[v for k,v in parts if k==b"HEDR"]
        from .identity_policy import header_cursor
        cursor=header_cursor(headers[0]) if len(headers)==1 and len(headers[0])==12 else None
        groups=[]
        from .record_graph import Slots
        from .historical_schema import group_label
        slots=Slots(path.name,master)
        names=[plugin_name(x) for x in [*master,path.name]]
        if len(set(names))!=len(names) or len(names)>254:raise ValueError("duplicate/too many masters")
        def walk(end,depth=0,parents=()):
            if depth>64:raise ValueError("group nesting limit")
            while f.tell()<end:
                offset=f.tell()
                if end-offset<24:raise ValueError("truncated header")
                h=read(24);sig,n,flags,form,vc,ver,unknown=HEADER.unpack(h)
                if sig==b"GRUP":
                    stop=offset+n
                    if n<24 or stop>end:raise ValueError("invalid group")
                    kind=struct.unpack_from("<i",h,12)[0]
                    label=h[8:12]
                    entry={"offset":offset,"type":kind,"label":label.hex(),"parents":list(parents)}
                    try:
                        role,value=group_label(kind,label,slots)
                        entry["role"]=role
                        if hasattr(value,"origin"):entry["owner"]={"origin":value.origin,"local_id":value.local}
                    except ValueError as e:entry["warning"]=str(e)
                    groups.append(entry)
                    yield from walk(stop,depth+1,(*parents,offset));continue
                if n>MAX_RECORD or f.tell()+n>end:raise ValueError("invalid record size")
                data=read(n);slot=form>>24;local=form&0xffffff
                if slot>=len(names) or not local:raise ValueError("unsupported/null FormID")
                edid=None
                if not flags&0x40000:
                    for k,v in subs(data):
                        if k==b"EDID":edid=text(v);break
                yield {"origin":names[slot],"local_id":local,"signature":sig.decode("ascii"),
                       "flags":flags,"editor_id":edid,"offset":offset,"groups":list(parents),"payload_sha256":hashlib.sha256(data).hexdigest()}
            if f.tell()!=end:raise ValueError("group boundary mismatch")
        records=list(walk(size))
        return {"name":path.name,"masters":master,"records":records,"groups":groups,"next_object_id":cursor}

class RecordIndex:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS fnv_files_v1(name TEXT PRIMARY KEY,digest TEXT NOT NULL,masters TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS fnv_records_v1(provider TEXT,origin TEXT,local_id INTEGER,signature TEXT,flags INTEGER,editor_id TEXT,offset INTEGER,payload_sha256 TEXT,PRIMARY KEY(provider,origin,local_id));
        CREATE INDEX IF NOT EXISTS fnv_origin_v1 ON fnv_records_v1(origin,local_id);
        CREATE INDEX IF NOT EXISTS fnv_editor_v1 ON fnv_records_v1(editor_id COLLATE NOCASE);
        """)
    def refresh(self,paths):
        paths=[Path(p).resolve(strict=True) for p in paths]
        names=[plugin_name(p.name) for p in paths]
        if len(set(names))!=len(names):raise ValueError("duplicate plugin")
        reports=[];changed=[]
        with self.db:
            for p,name in zip(paths,names):
                digest=fingerprint(p)
                cached=self.db.execute("SELECT digest,masters FROM fnv_files_v1 WHERE name=?",(name,)).fetchone()
                if cached and cached[0]==digest:
                    reports.append({"name":p.name,"masters":json.loads(cached[1])});continue
                result=scan(p)
                if fingerprint(p)!=digest:raise ValueError("plugin changed during scan")
                self.db.execute("DELETE FROM fnv_records_v1 WHERE provider=?",(name,))
                self.db.executemany("INSERT INTO fnv_records_v1 VALUES (?,?,?,?,?,?,?,?)",[(name,r["origin"],r["local_id"],r["signature"],r["flags"],r["editor_id"],r["offset"],r["payload_sha256"]) for r in result["records"]])
                self.db.execute("INSERT OR REPLACE INTO fnv_files_v1 VALUES (?,?,?)",(name,digest,json.dumps(result["masters"])))
                reports.append({"name":p.name,"masters":result["masters"]});changed.append(p.name)
            if [plugin_name(n) for n in dependency_order(reports)]!=names:raise ValueError("load order violates masters")
            for (n,) in self.db.execute("SELECT name FROM fnv_files_v1").fetchall():
                if n not in names:
                    self.db.execute("DELETE FROM fnv_files_v1 WHERE name=?",(n,))
                    self.db.execute("DELETE FROM fnv_records_v1 WHERE provider=?",(n,))
        self.order=names
        return {"plugins":len(names),"reindexed":changed,"cache_hits":len(names)-len(changed),"records":self.db.execute("SELECT count(*) FROM fnv_records_v1").fetchone()[0]}
    def chain(self,origin,local_id):
        if not hasattr(self,"order"):raise ValueError("refresh profile before querying")
        rows=self.db.execute("SELECT provider,signature,flags,editor_id,offset,payload_sha256 FROM fnv_records_v1 WHERE origin=? AND local_id=?",(plugin_name(origin),local_id)).fetchall()
        rows.sort(key=lambda r:self.order.index(r[0]))
        return [{"provider":r[0],"signature":r[1],"flags":r[2],"editor_id":r[3],"offset":r[4],"payload_sha256":r[5],"winning":i==len(rows)-1} for i,r in enumerate(rows)]
    def close(self):self.db.close()
