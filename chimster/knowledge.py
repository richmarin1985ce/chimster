"""Local searchable reference notes, indexed with SQLite FTS5."""
import sqlite3,re
from pathlib import Path

class KnowledgeIndex:
    def __init__(self,path):
        self.db=sqlite3.connect(path)
        self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_v1 USING fts5(path UNINDEXED,body,tokenize='unicode61')")
    def rebuild(self,root):
        root=Path(root).resolve(strict=True)
        if not root.is_dir():raise ValueError("expected documentation directory")
        count=0;total=0
        with self.db:
            self.db.execute("DELETE FROM knowledge_v1")
            for p in sorted(root.rglob("*")):
                if p.is_symlink() or not p.is_file() or p.suffix.lower() not in {".md",".txt",".rst"}:continue
                if not p.resolve().is_relative_to(root) or p.stat().st_size>1024*1024:continue
                total+=p.stat().st_size
                if total>64*1024*1024 or count>=10000:raise ValueError("documentation corpus exceeds limits")
                body=p.read_text(encoding="utf-8",errors="replace")
                self.db.execute("INSERT INTO knowledge_v1(path,body) VALUES (?,?)",(p.relative_to(root).as_posix(),body))
                count+=1
        return {"documents":count,"source_bytes":total}
    def search(self,query,limit=10):
        terms=re.findall(r"\w+",query,flags=re.UNICODE)[:20]
        if not terms or not 1<=limit<=50:raise ValueError("invalid query")
        match=" AND ".join('"'+t+'"' for t in terms)
        rows=self.db.execute("SELECT path,snippet(knowledge_v1,1,'[',']',' … ',30) FROM knowledge_v1 WHERE knowledge_v1 MATCH ? ORDER BY bm25(knowledge_v1) LIMIT ?",(match,limit))
        return [{"source":p,"excerpt":s} for p,s in rows]
    def close(self):self.db.close()
