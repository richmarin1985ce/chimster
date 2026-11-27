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

    def test_heading_fragments(self):
        with TemporaryDirectory() as d:
            p=Path(d);src=p/"docs";src.mkdir()
            (src/"a.md").write_text("# Repeat\n# Repeat\n# Repeat-1\n[Here](#repeat-1) [Other](b.md#other) [Missing](#missing)")
            (src/"b.md").write_text("# Other")
            with Wiki(src) as w:
                report=export(w,p/"out")
                self.assertEqual(report["internal_links"],2)
                self.assertEqual(len(report["unresolved_links"]),1)
                page=(p/"out/a.md.html").read_text()
                for anchor in ("repeat","repeat-1","repeat-1-1"):
                    self.assertIn('id="'+anchor+'"',page)
                self.assertIn('href="b.md.html#other"',page)
