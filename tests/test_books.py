import unittest,json
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.books import Book,save,load,preview,export
class BookTests(unittest.TestCase):
    def test_roundtrip(self):
        b=Book("ChimsterTest","A Book",("First page","Second page"),"Author")
        with TemporaryDirectory() as d:
            p=Path(d)/"out";export(b,p)
            self.assertEqual(load(p/"book.json"),b)
            self.assertEqual(json.loads((p/"localization.json").read_text()),b.localization())
            self.assertIn("2 / 2",preview(b))
    def test_translation(self):
        b=Book("Test","Title",("A {name}",))
        s=b.localization();s["Test.page.0001"]="B {name}"
        self.assertEqual(b.translated(s).pages,("B {name}",))
        del s["Test.title"]
        with self.assertRaises(ValueError):b.translated(s)
    def test_validation(self):
        with self.assertRaises(ValueError):Book("../bad","Title",("Text",)).validate()
        b=Book("Test","<script>",("<img src=x>",))
        self.assertNotIn("<img src=x>",preview(b))
        self.assertIn("&lt;img src=x&gt;",preview(b))
