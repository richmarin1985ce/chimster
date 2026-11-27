import unittest,importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.books import Book
from chimster.book_layout import export
@unittest.skipUnless(importlib.util.find_spec("PIL"),"optional Pillow")
class LayoutTests(unittest.TestCase):
    def test_illustration(self):
        from PIL import Image
        with TemporaryDirectory() as d:
            p=Path(d);a=p/"assets";a.mkdir();Image.new("RGBA",(8,8),(255,0,0,255)).save(a/"cover.png")
            book=Book("Book","Test",("<script>text</script>",))
            layout={"schema":1,"cover":"cover.png","illustrations":[{"page":1,"image":"cover.png","caption":"<Caption>"}]}
            r=export(book,layout,a,p/"out")
            self.assertEqual(r["images"],2)
            s=(p/"out/preview.html").read_text();self.assertIn("&lt;script&gt;",s);self.assertIn("&lt;Caption&gt;",s)
            with self.assertRaises(ValueError):export(book,{"schema":1,"cover":"../cover.png"},a,p/"bad")
