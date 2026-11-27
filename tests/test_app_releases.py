import unittest,zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.app_releases import build,Installation,verify_archive,safe_path
class ReleasesTests(unittest.TestCase):
    def test_update_rollback(self):
        with TemporaryDirectory() as d:
            p=Path(d);src=p/"src";src.mkdir();(src/"chimster").write_text("one")
            a=build(src,p/"v1.zip","0.3.0","chimster");inst=Installation(p/"app")
            inst.install(p/"v1.zip",a["sha256"],True)
            (src/"chimster").write_text("two")
            b=build(src,p/"v2.zip","0.3.1","chimster")
            with self.assertRaises(ValueError):inst.install(p/"v2.zip","0"*64)
            inst.install(p/"v2.zip",b["sha256"],True);self.assertEqual(inst.status()["current"]["version"],"0.3.1")
            inst.activate("0.3.0");self.assertEqual(inst.status()["current"]["version"],"0.3.0")
            (p/"app/versions/0.3.1/chimster").write_text("tampered")
            with self.assertRaises(ValueError):inst.activate("0.3.1")
    def test_paths(self):
        for path in ("../bad","AUX.txt","foo//bar","a\\b","a/..","/x"):
            with self.assertRaises(ValueError):safe_path(path)
        with TemporaryDirectory() as d:
            p=Path(d)/"bad.zip"
            with zipfile.ZipFile(p,"w") as z:z.writestr("../escape","bad")
            with self.assertRaises(ValueError):verify_archive(p)
