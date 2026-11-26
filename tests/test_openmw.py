import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from chimster.openmw import Profile, launch_game, reload_plan

class OpenMWTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.data=self.root/"original data"
        self.data.mkdir()
        (self.data/"Morrowind.esm").touch()
        (self.data/"Morrowind.bsa").touch()
        self.profile=Profile(self.root/"workspace",(self.data,),("Morrowind.esm",),("Morrowind.bsa",))
    def test_explicit_args(self):
        args=self.profile.engine_args()
        self.assertEqual(args[args.index("--data")+1],str(self.data.resolve()))
        self.assertIn("Morrowind.esm",args)
        self.assertIn("--replace",args)
    def test_no_write_preview(self):
        self.profile.engine_args()
        self.assertFalse(self.profile.root.exists())
    def test_prepare(self):
        self.profile.prepare()
        self.assertTrue(self.profile.staging.is_dir())
        self.assertTrue(self.profile.userdata.is_dir())
    def test_missing(self):
        with self.assertRaises(ValueError):
            Profile(self.profile.root,(self.data,),("missing.esp",)).validate()
    def test_traversal(self):
        with self.assertRaises(ValueError):
            Profile(self.profile.root,(self.data,),("../Morrowind.esm",)).validate()
    def test_no_overlap(self):
        with self.assertRaises(ValueError):
            Profile(self.data/"workspace",(self.data,),("Morrowind.esm",)).validate()
    def test_reload(self):
        self.assertEqual(reload_plan(["a.lua"])["command"],"reloadlua")
        self.assertEqual(reload_plan(["a.lua","b.omwscripts"])["action"],"restart")
    @patch("chimster.openmw.subprocess.Popen")
    def test_launch(self,popen):
        executable=self.root/"openmw"
        executable.touch()
        launch_game(self.profile,executable)
        self.assertFalse(popen.call_args.kwargs["shell"])
        self.assertEqual(popen.call_args.args[0][0],str(executable.resolve()))
