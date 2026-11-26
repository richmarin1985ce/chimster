import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.wiki import Wiki,manual_root

class WikiTests(unittest.TestCase):
    def test_bundled(self):
        with Wiki() as w:
            ids={p["id"] for p in w.pages()}
            self.assertIn("lod-forge.md",ids)
            self.assertIn("texture-forge.md",ids)
            self.assertTrue(w.search("How do I build terrain LOD?"))
            self.assertIn("LOD",w.read("lod-forge.md")["body"])
    def test_local(self):
        with TemporaryDirectory() as d:
            root=Path(d);(root/"note.md").write_text("# Test\nNormal specular textures",encoding="utf-8")
            with Wiki(root) as w:
                self.assertEqual(w.pages(),[{"id":"note.md","title":"Test"}])
                self.assertEqual(w.search("How do I generate normal maps?")[0]["id"],"note.md")
                self.assertEqual(w.search("the a"),[])
                for p in ("../note.md","/etc/passwd","not-found.md"):
                    with self.assertRaises(ValueError):w.read(p)
