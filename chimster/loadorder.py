"""MIT read-only header cache and stable dependency sorting; not a full LOOT replacement."""
from pathlib import Path
from hashlib import sha256
from heapq import heappush, heappop
import json, sqlite3
from .core import inspect_plugin, PROFILES

CACHE_SCHEMA="header-v1"
def plugin_name(n):
    if not isinstance(n,str) or not n or n.strip()!=n or any(c in n for c in '/\\:\r\n\0') or Path(n).suffix.lower() not in {".esp",".esm",".esl",".omwaddon",".omwgame"}:
        raise ValueError("invalid plugin name")
    return n.casefold()

def dependency_order(plugins, after=()):
    """plugins: [{name, masters}]; after: (earlier,later) pairs.
    Keeps input priority where the graph allows. No engine-specific master flags or LOOT heuristics."""
    names={}; rank={}; edges={}; indegree={}
    for i,p in enumerate(plugins):
        k=plugin_name(p["name"])
        if k in names: raise ValueError("duplicate plugin: "+p["name"])
        names[k]=p["name"];rank[k]=i;edges[k]=set();indegree[k]=0
    def edge(a,b):
        a,b=plugin_name(a),plugin_name(b)
        if a not in names or b not in names: raise ValueError("missing dependency: "+str((a,b)))
        if b not in edges[a]:
            edges[a].add(b);indegree[b]+=1
    for p in plugins:
        for m in p["masters"]: edge(m,p["name"])
    for a,b in after: edge(a,b)
    queue=[]
    for k,v in indegree.items():
        if not v: heappush(queue,(rank[k],k))
    result=[]
    while queue:
        _,k=heappop(queue);result.append(names[k])
        for b in edges[k]:
            indegree[b]-=1
            if not indegree[b]: heappush(queue,(rank[b],b))
    if len(result)!=len(names):
        raise ValueError("cycle or blocked by cycle: "+", ".join(names[k] for k,v in indegree.items() if v))
    return result

def fingerprint(path):
    h=sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

class HeaderCache:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS header_cache_v1 (game TEXT, schema TEXT, digest TEXT, payload TEXT, PRIMARY KEY(game,schema,digest))")
    def inspect(self,path,game):
        path=Path(path).resolve(strict=True)
        if game not in PROFILES: raise ValueError("unsupported game")
        digest=fingerprint(path)
        row=self.db.execute("SELECT payload FROM header_cache_v1 WHERE game=? AND schema=? AND digest=?",(game,CACHE_SCHEMA,digest)).fetchone()
        hit=row is not None
        if hit:
            data=json.loads(row[0])
        else:
            data=inspect_plugin(path,game)
            data.pop("file",None)
            if fingerprint(path)!=digest: raise ValueError("file changed during scan")
            with self.db:
                self.db.execute("INSERT OR REPLACE INTO header_cache_v1 VALUES (?,?,?,?)",(game,CACHE_SCHEMA,digest,json.dumps(data,sort_keys=True)))
        return {"name":path.name,"sha256":digest,"cache_hit":hit,**data}
    def close(self): self.db.close()

def scan_profile(game,data_dirs,names,cache,after=()):
    """Explicit directories from lowest to highest priority; no changes to files."""
    dirs=[Path(d).resolve(strict=True) for d in data_dirs]
    if not dirs or any(not d.is_dir() for d in dirs): raise ValueError("invalid data directories")
    if len({plugin_name(n) for n in names})!=len(names): raise ValueError("duplicate plugins")
    # Index filenames once per directory, preserving virtual overlay precedence.
    index={}
    for d in dirs:
        local={}
        for p in d.iterdir():
            if p.is_file() and p.suffix.lower() in {".esp",".esm",".esl",".omwaddon",".omwgame"}:
                k=p.name.casefold()
                if k in local: raise ValueError("case collision: "+p.name)
                local[k]=p
        index.update(local)
    reports=[]
    for name in names:
        k=plugin_name(name)
        if k not in index: raise ValueError("missing active plugin: "+name)
        report=cache.inspect(index[k],game);report["name"]=name;reports.append(report)
    return {"game":game,"plugins":reports,"proposed_order":dependency_order(reports,after),"cache_hits":sum(r["cache_hit"] for r in reports),"writes_load_order":False,"warning":"Dependency-only order; engine flag constraints, LOOT metadata, asset priority and runtime validation not integrated."}
