import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from chimster.xedit import Workspace, preview, launch, report_from_log

class XEditTests(unittest.TestCase):
    def setUp(self):
        d=TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        (self.root/"Data").mkdir()
        (self.root/"plugins.txt").write_text("Example.esp\n")
        self.exe=self.root/"xEdit.exe"
        self.exe.touch()
        self.ws=Workspace(self.root,"newvegas")
    def test_preview(self):
        args=preview(self.ws,self.exe)["args"]
        self.assertIn("-FNV",args)
        self.assertIn("-D:"+str(self.root/"Data"),args)
        self.assertFalse((self.root/"Cache").exists())
    def test_lod_output(self):
        args=preview(self.ws,self.exe,"lod")["args"]
        self.assertIn("-O:"+str(self.root/"LODOutput"),args)
    def test_unsupported(self):
        with self.assertRaises(ValueError):
            preview(Workspace(self.root,"morrowind"),self.exe)
        with self.assertRaises(ValueError):
            preview(Workspace(self.root,"starfield"),self.exe,"lod")
    def test_report(self):
        rows=report_from_log("unrelated\nCHIMSTER_AUDIT|STAT|Example.esp|01000800|TreeA|tree.nif|1")
        self.assertEqual(rows[0]["model"],"tree.nif")
        self.assertTrue(rows[0]["winning"])
    def test_bad_report(self):
        with self.assertRaises(ValueError):
            report_from_log("CHIMSTER_AUDIT|STAT|bad")
    def test_hardlink(self):
        source=self.root/"source.esp"
        source.touch()
        (self.root/"Data"/"alias.esp").hardlink_to(source)
        with self.assertRaises(ValueError):
            preview(self.ws,self.exe)
    @patch("chimster.xedit.subprocess.Popen")
    def test_launch(self,popen):
        launch(self.ws,self.exe,"conflicts")
        self.assertFalse(popen.call_args.kwargs["shell"])
        self.assertIn("-quickshowconflicts",popen.call_args.args[0])
