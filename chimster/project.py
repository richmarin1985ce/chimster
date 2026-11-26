"""Versioned local project store. Immutable imported objects; atomic manifest revisions."""
from pathlib import Path
from contextlib import contextmanager
import hashlib,json,os,re,shutil,tempfile
from .core import PROFILES
ID=re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}")
KINDS={"terrain","scene","landscape","records","quest","book","interior","mesh","texture","material","audio","localization","plugin","ledger","package","other"}
def identifier(v):
    if not isinstance(v,str) or not ID.fullmatch(v) or v.endswith("."):raise ValueError("invalid identifier")
    return v
def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()
def atomic_json(path,value):
    fd,name=tempfile.mkstemp(prefix=".write-",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write("\n");f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)
def read_json(path,limit=16*1024*1024):
    if path.is_symlink() or path.stat().st_size>limit:raise ValueError("unsafe or oversized JSON")
    return json.loads(path.read_text(encoding="utf-8"))
class Project:
    def __init__(self,root):
        self.root=Path(root).resolve(strict=True)
        self.meta=self.root/".chimster"
        for p in (self.meta,self.meta/"objects",self.meta/"revisions"):
            if p.is_symlink() or not p.is_dir():raise ValueError("invalid project storage")
        self.head=self.meta/"project.json";self.read()
    @classmethod
    def create(cls,root,name,game):
        identifier(name)
        if game not in PROFILES:raise ValueError("unknown game")
        p=Path(root)
        if p.is_symlink():raise ValueError("symlink project root")
        p.mkdir(parents=True,exist_ok=True)
        meta=p/".chimster";meta.mkdir(exist_ok=False)
        try:
            for d in ("objects","revisions"):(meta/d).mkdir()
            m={"schema":1,"name":name,"game":game,"revision":0,"artifacts":{}}
            atomic_json(meta/"revisions"/"0.json",m);atomic_json(meta/"project.json",m)
        except Exception:shutil.rmtree(meta);raise
        return cls(p)
    def read(self):
        m=read_json(self.head)
        if m.get("schema")!=1 or m.get("game") not in PROFILES or type(m.get("revision")) is not int or m["revision"]<0:raise ValueError("unsupported project manifest")
        identifier(m["name"])
        if not isinstance(m.get("artifacts"),dict) or len(m["artifacts"])>50000:raise ValueError("invalid artifact table")
        for k,a in m["artifacts"].items():
            identifier(k)
            if a.get("kind") not in KINDS or not re.fullmatch(r"[0-9a-f]{64}",a.get("sha256","")) or type(a.get("size")) is not int or a["size"]<0:raise ValueError("invalid artifact")
            if not isinstance(a.get("filename"),str) or Path(a["filename"]).name!=a["filename"] or any(c in a["filename"] for c in "\\/:") or not a["filename"]:raise ValueError("invalid filename")
        return m
    @contextmanager
    def lock(self):
        p=self.meta/"write.lock"
        try:fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError as e:raise ValueError("project is locked; check for another writer or stale lock") from e
        try:
            os.write(fd,str(os.getpid()).encode());yield
        finally:os.close(fd);p.unlink()
    def commit(self,m,expected):
        # Call only with the project write lock held. An orphan snapshot after a
        # crash is harmless, but never reuse/overwrite a revision number.
        current=self.read()
        if current["revision"]!=expected:raise ValueError("stale project revision")
        n=expected+1
        while (self.meta/"revisions"/f"{n}.json").exists():n+=1
        m["revision"]=n
        atomic_json(self.meta/"revisions"/f"{n}.json",m);atomic_json(self.head,m)
        return m
    def add(self,key,kind,source,expected,replace=False):
        identifier(key)
        if kind not in KINDS:raise ValueError("unknown artifact kind")
        p=Path(source)
        if p.is_symlink() or not p.is_file():raise ValueError("regular source file required")
        with self.lock():
            m=self.read()
            if m["revision"]!=expected:raise ValueError("stale project revision")
            if key in m["artifacts"] and not replace:raise ValueError("artifact exists; explicit replace required")
            if any(k.casefold()==key.casefold() and k!=key for k in m["artifacts"]):raise ValueError("case-insensitive ID collision")
            fd,name=tempfile.mkstemp(prefix=".object-",dir=self.meta/"objects");os.close(fd);tmp=Path(name)
            try:
                shutil.copyfile(p,tmp);h=digest(tmp);size=tmp.stat().st_size
                dest=self.meta/"objects"/h
                if dest.is_symlink():raise ValueError("unsafe object")
                if dest.exists():
                    if not dest.is_file() or digest(dest)!=h:raise ValueError("corrupt object")
                else:os.replace(tmp,dest)
                m["artifacts"][key]={"kind":kind,"filename":p.name,"size":size,"sha256":h}
                return self.commit(m,expected)
            finally:tmp.unlink(missing_ok=True)
    def object(self,key,verify=True):
        a=self.read()["artifacts"][identifier(key)];p=self.meta/"objects"/a["sha256"]
        if p.is_symlink() or not p.is_file() or p.stat().st_size!=a["size"] or verify and digest(p)!=a["sha256"]:raise ValueError("missing/corrupt artifact")
        return p
    def export(self,key,destination):
        source=self.object(key);q=Path(destination)
        if q.is_symlink():raise ValueError("unsafe output")
        created=False
        try:
            with q.open("xb") as f:
                created=True
                with source.open("rb") as src:shutil.copyfileobj(src,f)
            if digest(q)!=source.name:raise ValueError("export verification failed")
        except Exception:
            if created:q.unlink(missing_ok=True)
            raise
        return str(q)
    def remove(self,key,expected):
        with self.lock():
            m=self.read()
            if m["revision"]!=expected:raise ValueError("stale project revision")
            del m["artifacts"][identifier(key)]
            return self.commit(m,expected)
    def rollback(self,revision,expected):
        if type(revision) is not int or not 0<=revision<=expected:raise ValueError("invalid revision")
        with self.lock():
            m=read_json(self.meta/"revisions"/f"{revision}.json")
            current=self.read()
            if m["game"]!=current["game"] or m["name"]!=current["name"]:raise ValueError("wrong project snapshot")
            for a in m["artifacts"].values():
                h=a["sha256"]
                if not re.fullmatch(r"[0-9a-f]{64}",h):raise ValueError("invalid snapshot")
                p=self.meta/"objects"/h
                if p.is_symlink() or not p.is_file() or digest(p)!=h:raise ValueError("corrupt snapshot object")
            return self.commit(m,expected)
    def verify(self):
        m=self.read();issues=[]
        for k in m["artifacts"]:
            try:self.object(k)
            except (ValueError,OSError) as e:issues.append({"id":k,"error":str(e)})
        return {"valid":not issues,"revision":m["revision"],"artifacts":len(m["artifacts"]),"issues":issues}
