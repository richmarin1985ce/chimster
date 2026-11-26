import unittest,struct
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.compatibility import snapshot,compare,archive_header,remaster_package,inspect
class CompatibilityTests(unittest.TestCase):
    def test_release_changes(self):
        with TemporaryDirectory() as d:
            p=Path(d);a=p/"test.ba2"
            a.write_bytes(struct.pack("<4sI4sIQ",b"BTDX",1,b"GNRL",0,24))
            old=snapshot(p,"fallout76","1")
            self.assertTrue(archive_header(a)["recognized_layout"])
            a.write_bytes(struct.pack("<4sI4sIQ",b"BTDX",999,b"GNRL",0,24))
            self.assertFalse(inspect(a,"fallout76")["recognized_layout"])
            new=snapshot(p,"fallout76","2")
            self.assertEqual(compare(old,new)["changed"],["test.ba2"])
            self.assertFalse(compare(old,new)["native_write_approved"])
    def test_remaster(self):
        with TemporaryDirectory() as d:
            p=Path(d);a=p/"Test.esp";b=p/"Test.ucas";a.touch();b.touch()
            r=remaster_package([a,b])
            self.assertIn("ObvData/Data",r["files"][0]["destination"])
            self.assertIn("~mods",r["files"][1]["destination"])
            self.assertEqual(r["incomplete_iostore_pairs"],["test"])
            self.assertFalse(r["writes_allowed"])
