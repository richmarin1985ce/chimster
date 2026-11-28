import tempfile
from pathlib import Path
import unittest
from chimster import voice_takes as vt
from test_audio import wav

class VoiceTakeTests(unittest.TestCase):
    def test_takes(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);source=base/"voice.wav";source.write_bytes(wav())
            root=base/"takes";staged=base/"staged"
            kwargs={"line":"Test.esp/Voice/Line","performer":"Actor A","rights":"Original recording with permission"}
            a=vt.register(root,source,**kwargs)
            b=vt.register(root,source,**kwargs)
            self.assertNotEqual(a["id"],b["id"])
            self.assertEqual(len(vt.list_takes(root,kwargs["line"])),2)
            self.assertEqual(Path(vt.select(root,a["id"],staged)["path"]).read_bytes(),wav())
            with self.assertRaises(FileExistsError):vt.select(root,b["id"],staged)
            with self.assertRaises(ValueError):vt.select(root,a["id"],root/"staged")
            (root/a["id"]/"take.wav").write_bytes(b"changed")
            with self.assertRaises(ValueError):vt.get(root,a["id"])
            with self.assertRaises(ValueError):vt.register(root,source,**{**kwargs,"rights":""})
