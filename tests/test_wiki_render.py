import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.wiki import Wiki
from chimster.wiki_render import render,resolve,export,link_report
class RenderTests(unittest.TestCase):
    def test_local_links(self):
        with TemporaryDirectory() as d:
            p=Path(d);src=p/"docs";src.mkdir()
            (src/"a.md").write_text("# Title\n[Other](b.md) [Bad](../x) **bold**\n<script>alert(1)</script>")
            (src/"b.md").write_text("# Other")
            with Wiki(src) as w:
                r=export(w,p/"out");self.assertEqual(r["internal_links"],1)
                self.assertEqual(len(r["unresolved_links"]),1)
                s=(p/"out/a.md.html").read_text();self.assertIn('href="b.md.html"',s);self.assertIn("&lt;script&gt;",s);self.assertNotIn("<script>",s)
            self.assertIsNone(resolve("a.md","https://example.com",{"a.md"}))
