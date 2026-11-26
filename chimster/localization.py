"""Context-sensitive translation memory. Translation itself is provider-agnostic."""
from pathlib import Path
import sqlite3

class TranslationMemory:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.execute("CREATE TABLE IF NOT EXISTS memory (src_lang TEXT, dst_lang TEXT, context TEXT, source TEXT, target TEXT, PRIMARY KEY(src_lang,dst_lang,context,source))")
    def remember(self, src_lang, dst_lang, context, source, target):
        with self.db:
            self.db.execute("INSERT INTO memory VALUES(?,?,?,?,?) ON CONFLICT(src_lang,dst_lang,context,source) DO UPDATE SET target=excluded.target", (src_lang,dst_lang,context,source,target))
    def lookup(self, src_lang, dst_lang, context, source):
        row = self.db.execute("SELECT target FROM memory WHERE src_lang=? AND dst_lang=? AND context=? AND source=?", (src_lang,dst_lang,context,source)).fetchone()
        return row[0] if row else None
    def close(self):
        self.db.close()
