import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.xedit import Workspace
from chimster.lod_tools import tool_plan,workflow,openmw_settings,mge_plan
class LodToolTests(unittest.TestCase):
    def test_plan(self):
        with TemporaryDirectory() as d:
            p=Path(d);(p/"Data").mkdir();(p/"INI").mkdir();(p/"plugins.txt").touch();e=p/"TexGen.exe";e.touch()
            r=tool_plan(Workspace(p,"skyrimse"),"texgen",e)
            self.assertIn("-sse",r["args"])
            self.assertFalse(Path(r["output"]).exists())
            with self.assertRaises(ValueError):tool_plan(Workspace(p,"newvegas"),"texgen",e)
    def test_paging(self):
        self.assertIn("object paging = true",openmw_settings())
        self.assertEqual(workflow("skyrimse")[2],"texgen")
    def test_mge(self):
        with TemporaryDirectory() as d:
            p=Path(d);(p/"MGEXEgui.exe").touch();(p/"Data Files").mkdir()
            self.assertTrue(mge_plan(p)["requires_interactive_review"])
