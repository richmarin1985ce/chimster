"""Offline documentation, safe page IDs, and local full-text retrieval."""
from pathlib import Path
import re,sqlite3
from .knowledge import KnowledgeIndex

def manual_root():
    bundled=Path(__file__).resolve().parent/"manual"
    source=Path(__file__).resolve().parents[1]/"docs"
    for root in (bundled,source):
        if root.is_dir() and any(root.glob("*.md")):return root
    raise FileNotFoundError("Chimster documentation is missing")

class Wiki:
    def __init__(self,root=None):
        self.root=Path(root or manual_root()).resolve(strict=True)
        self.index=KnowledgeIndex(":memory:")
        try:self.index.rebuild(self.root)
        except Exception:
            self.index.close();raise
    def pages(self):
        rows=self.index.db.execute("SELECT path,body FROM knowledge_v1 ORDER BY path")
        return [{"id":p,"title":next((line[2:].strip() for line in body.splitlines() if line.startswith("# ")),Path(p).stem)} for p,body in rows]
    def read(self,page):
        if not isinstance(page,str) or len(page)>1024:raise ValueError("invalid page ID")
        row=self.index.db.execute("SELECT body FROM knowledge_v1 WHERE path=?",(page,)).fetchone()
        if row is None:raise ValueError("unknown wiki page")
        return {"id":page,"body":row[0]}
    def search(self,query,limit=8):
        if not isinstance(query,str) or len(query)>4000 or not 1<=limit<=30:raise ValueError("invalid query")
        stop={"a","an","the","to","of","and","for","in","how","do","i","can","what","is","my","with"}
        words=list(dict.fromkeys(w.casefold() for w in re.findall(r"\w+",query) if w.casefold() not in stop))[:20]
        if not words:return []
        match=" OR ".join('"'+w+'"' for w in words)
        rows=self.index.db.execute("SELECT path,snippet(knowledge_v1,1,'[',']',' … ',45) FROM knowledge_v1 WHERE knowledge_v1 MATCH ? ORDER BY bm25(knowledge_v1),path LIMIT ?",(match,limit))
        return [{"id":p,"excerpt":s} for p,s in rows]
    def context(self,query,limit=5):
        return self.search(query,limit)
    def close(self):self.index.close()
    def __enter__(self):return self
    def __exit__(self,*exc):self.close()
