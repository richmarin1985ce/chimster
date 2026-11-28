import tempfile
import tkinter
import unittest
from pathlib import Path
from chimster.font_forge import create
from chimster.font_library import FontLibrary, drop_paths, read_font, MAX_BYTES

class FontForgeTests(unittest.TestCase):
    def test_create_import_duplicate_and_reload(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            font=root/"My Font.ttf"
            create("Test Family",{65:[[(0,0),(300,700),(600,0)]]},font)
            library=FontLibrary(root/"library")
            target,info=library.import_font(font)
            self.assertEqual(info["family"],"Test Family")
            self.assertEqual(info["characters"],2)
            self.assertEqual(library.import_font(font)[0],target)
            self.assertEqual(len(list(FontLibrary(root/"library").entries())),1)
            self.assertEqual(font.read_bytes(),target.read_bytes())
    def test_reject_bad_and_oversize(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            bad=root/"invalid.otf"
            bad.write_bytes(b"not a font")
            with self.assertRaises(ValueError):
                FontLibrary(root/"library").import_font(bad)
            self.assertFalse((root/"library").exists())
            with bad.open("wb") as stream:
                stream.truncate(MAX_BYTES+1)
            with self.assertRaises(ValueError):
                read_font(bad)
    def test_tcl_drop_paths(self):
        root=tkinter.Tcl()
        self.assertEqual(drop_paths(root,"{/tmp/My Font.ttf} /tmp/other.otf"),(Path("/tmp/My Font.ttf"),Path("/tmp/other.otf")))
