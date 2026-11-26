"""Offline, versioned application installs with explicit trusted package digests.

No network, no privilege elevation, no system-wide installation, no automatic
execution. SHA-256 establishes integrity relative to a separately trusted digest,
not publisher identity or a digital signature.
"""
from pathlib import Path,PurePosixPath
from contextlib import contextmanager
import os,re,stat,json,zipfile,hashlib,shutil,tempfile,platform
from .project import digest,atomic_json,read_json
VER=re.compile(r"[0-9]+(?:\.[0-9]+){1,3}(?:[-.][A-Za-z0-9]+)*")
MANIFEST="chimster-app-release.json"
def token(v):
    if not isinstance(v,str) or len(v)>80 or not VER.fullmatch(v):raise ValueError("invalid version")
    return v
def target_platform():
    machine=platform.machine().lower()
    machine={"amd64":"x86_64","aarch64":"arm64"}.get(machine,machine)
    return platform.system().lower()+"-"+machine
def safe_path(name):
    if not isinstance(name,str) or not name or "\\" in name or ":" in name or name.startswith("/") or any(ord(c)<32 for c in name):raise ValueError("unsafe release path")
    parts=name.split("/")
    reserved={"CON","PRN","AUX","NUL",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}
    if any(not p or p in (".","..") or p.endswith((".", " ")) or p.split(".")[0].upper() in reserved for p in parts):raise ValueError("unsafe release path")
    return PurePosixPath(name)
def validate_manifest(m):
    if m.get("schema")!=1 or m.get("product")!="chimster" or not isinstance(m.get("platform"),str):raise ValueError("invalid release manifest")
    token(m["version"]);entry=safe_path(m["entrypoint"]).as_posix()
    files=m["files"];seen=set();dirs=set()
    if not isinstance(files,list) or not 1<=len(files)<=50000:raise ValueError("invalid release file count")
    for f in files:
        p=safe_path(f["path"]);k=p.as_posix().casefold()
        if k==MANIFEST.casefold() or k in seen or k in dirs or any(a.as_posix().casefold() in seen for a in p.parents):raise ValueError("path collision")
        seen.add(k);dirs.update(a.as_posix().casefold() for a in p.parents)
        if type(f["size"]) is not int or f["size"]<0 or not re.fullmatch(r"[0-9a-f]{64}",f["sha256"]) or type(f.get("executable")) is not bool:raise ValueError("invalid file entry")
    if entry not in {f["path"] for f in files} or sum(f["size"] for f in files)>2*1024**3:raise ValueError("invalid entrypoint or size limit")
    return m
def build(root,output,version,entrypoint,platform_id=None):
    p=Path(root).resolve(strict=True);q=Path(output)
    if not p.is_dir() or q.resolve().is_relative_to(p) or q.exists() or q.is_symlink():raise ValueError("new package outside source tree required")
    rows=[]
    for f in sorted(p.rglob("*")):
        if f.is_symlink():raise ValueError("symlink in release")
        if f.is_file():rows.append({"path":f.relative_to(p).as_posix(),"size":f.stat().st_size,"sha256":digest(f),"executable":bool(f.stat().st_mode&0o111)})
        elif not f.is_dir():raise ValueError("unsupported file type")
    m=validate_manifest({"schema":1,"product":"chimster","version":token(version),"platform":platform_id or target_platform(),"entrypoint":entrypoint,"files":rows})
    created=False
    try:
        with zipfile.ZipFile(q,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            created=True
            for r in rows:
                f=p/r["path"]
                if f.stat().st_size!=r["size"] or digest(f)!=r["sha256"]:raise ValueError("source changed")
                z.write(f,r["path"])
            z.writestr(MANIFEST,json.dumps(m,sort_keys=True))
        verify_archive(q)
    except Exception:
        if created:q.unlink(missing_ok=True)
        raise
    return {"output":str(q),"sha256":digest(q),"manifest":m}
def archive_manifest(z):
    entries=z.infolist()
    if len(entries)>50001 or sum(i.file_size for i in entries)>2*1024**3+16*1024*1024:raise ValueError("archive exceeds limit")
    names=set()
    for i in entries:
        safe_path(i.filename);k=i.filename.casefold();mode=i.external_attr>>16
        if k in names or i.is_dir() or stat.S_ISLNK(mode) or i.flag_bits&1:raise ValueError("unsafe archive entry")
        names.add(k)
    if MANIFEST not in z.namelist() or z.getinfo(MANIFEST).file_size>16*1024*1024:raise ValueError("missing/oversized manifest")
    m=validate_manifest(json.loads(z.read(MANIFEST)))
    if set(z.namelist())!={MANIFEST,*[f["path"] for f in m["files"]]}:raise ValueError("archive manifest mismatch")
    return m
def verify_archive(path,expected=None,extract=None):
    p=Path(path)
    if expected is not None and (not re.fullmatch(r"[0-9a-fA-F]{64}",expected) or digest(p)!=expected.lower()):raise ValueError("package digest mismatch")
    with zipfile.ZipFile(p) as z:
        m=archive_manifest(z)
        for f in m["files"]:
            i=z.getinfo(f["path"])
            if i.file_size!=f["size"]:raise ValueError("file size mismatch")
            h=hashlib.sha256();n=0
            if extract is not None:
                out=extract/f["path"];out.parent.mkdir(parents=True,exist_ok=True)
                dst=out.open("xb")
            else:dst=None
            try:
                with z.open(i) as src:
                    for block in iter(lambda:src.read(1024*1024),b""):
                        n+=len(block)
                        if n>f["size"]:raise ValueError("size overflow")
                        h.update(block)
                        if dst:dst.write(block)
            finally:
                if dst:dst.close()
            if n!=f["size"] or h.hexdigest()!=f["sha256"]:raise ValueError("file digest mismatch")
            if extract is not None and f["executable"]:out.chmod(0o755)
    if expected is not None and digest(p)!=expected.lower():raise ValueError("package changed during verification")
    return m
class Installation:
    def __init__(self,root):
        p=Path(root)
        if p.is_symlink():raise ValueError("symlink install root")
        p.mkdir(parents=True,exist_ok=True);self.root=p.resolve();self.versions=self.root/"versions"
        if self.versions.is_symlink():raise ValueError("symlink versions")
        self.versions.mkdir(exist_ok=True);self.current=self.root/"current.json"
    @contextmanager
    def lock(self):
        p=self.root/"install.lock"
        try:fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError as e:raise ValueError("installation locked") from e
        try:yield
        finally:os.close(fd);p.unlink()
    def install(self,archive,expected,activate=False):
        if not isinstance(expected,str) or not re.fullmatch(r"[0-9a-fA-F]{64}",expected):raise ValueError("trusted package SHA-256 required")
        with self.lock():
            stage=Path(tempfile.mkdtemp(prefix=".install-",dir=self.versions))
            try:
                m=verify_archive(archive,expected,stage)
                if m["platform"]!=target_platform():raise ValueError("release is for another platform")
                dest=self.versions/token(m["version"])
                if dest.exists() or dest.is_symlink():raise ValueError("version already installed")
                atomic_json(stage/MANIFEST,m);stage.rename(dest)
                if activate:self._activate(m["version"])
                return {"version":m["version"],"path":str(dest),"active":activate}
            finally:
                if stage.exists():shutil.rmtree(stage)
    def verify(self,version):
        p=self.versions/token(version)
        if p.is_symlink() or not p.is_dir():raise ValueError("invalid installed version")
        m=validate_manifest(read_json(p/MANIFEST))
        if m["version"]!=version or m["platform"]!=target_platform():raise ValueError("wrong installed manifest")
        expected={f["path"] for f in m["files"]}|{MANIFEST}
        actual=set()
        for q in p.rglob("*"):
            if q.is_symlink():raise ValueError("symlink in installed version")
            if q.is_file():actual.add(q.relative_to(p).as_posix())
        if actual!=expected:raise ValueError("installed files differ from manifest")
        for f in m["files"]:
            q=p/f["path"]
            if q.stat().st_size!=f["size"] or digest(q)!=f["sha256"]:raise ValueError("installed file changed")
        return m
    def _activate(self,version):
        m=self.verify(version)
        atomic_json(self.current,{"schema":1,"version":version,"entrypoint":m["entrypoint"]})
        return {"version":version,"entrypoint":str(self.versions/version/m["entrypoint"])}
    def activate(self,version):
        with self.lock():return self._activate(version)
    def status(self):
        current=read_json(self.current) if self.current.exists() else None
        return {"current":current,"versions":sorted(p.name for p in self.versions.iterdir() if p.is_dir() and not p.is_symlink() and VER.fullmatch(p.name)),"scope":"local versioned installation; no automatic execution or publisher authentication"}
