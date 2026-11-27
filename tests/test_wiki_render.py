import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.wiki import Wiki
from chimster.wiki_render import target,render_html,audit,export
class WikiRenderTests(unittest.TestCase):
    def test_links_and_safe_markup(self):
        with TemporaryDirectory() as d:
            p=Path(d);docs=p/"docs";docs.mkdir()
            (docs/"a.md").write_text("# A\n[Go](b.md#heading)\n<script>alert(1)</script>\n[External](https://example.org)\n[Bad](../outside.md)")
            (docs/"b.md").write_text("# Heading\n**Bold**")
            with Wiki(docs) as w:
                r=audit(w);self.assertEqual(r["broken_links"],[{"page":"a.md","target":"../outside.md"}])
                self.assertEqual(r["external_links_not_checked"],1)
                out=export(w,p/"html")
                pages=list((p/"html").glob("page-*.html"));self.assertEqual(len(pages),2)
                raw=next(q.read_text() for q in pages if "alert(1)" in q.read_text())
                self.assertIn("&lt;script&gt;",raw);self.assertNotIn("href='https:",raw)
                self.assertIn("#heading",raw)
