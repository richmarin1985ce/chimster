import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fnv_patch import record,sub
from chimster.fnv_world import group
from chimster.formids import FormIDs
from chimster.native_identity import audit,continuation
class NativeIdentityTests(unittest.TestCase):
    def test_cursor_and_native_group(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"test.esp"
            payload=record(b"CELL",sub(b"EDID",b"Room\0"),0x800)
            children=group(6,struct.pack("<I",0x800),b"")
            p.write_bytes(record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,3,0x910)))+group(0,b"CELL",payload+children))
            report=audit(p)
            self.assertEqual(report["cursor"],0x910)
            self.assertEqual(report["issues"],[])
            self.assertEqual(report["groups"][1]["owner"]["local_id"],0x800)
            self.assertEqual(continuation(p,FormIDs(p.name),{"new":None}),{"new":0x910})
    def test_stale_cursor(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"test.esp"
            p.write_bytes(record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,2,0x800)))+group(0,b"MISC",record(b"MISC",b"",0x800)))
            self.assertTrue(audit(p)["issues"])
            with self.assertRaises(ValueError):continuation(p,FormIDs(p.name),{"new":None})
