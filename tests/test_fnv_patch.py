import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from test_fnv_records import make
from chimster.fnv_patch import build_gmst_patch
from chimster.fnv_records import scan
class PatchWriterTests(unittest.TestCase):
    def test_write(self):
        with TemporaryDirectory() as d:
            p=Path(d);a=p/"Base.esm";b=p/"Override.esp";out=p/"Chimster.esp";make(a);make(b,a.name,2)
            before=a.read_bytes(),b.read_bytes()
            result=build_gmst_patch([a,b],out,a.name,[0x800])
            self.assertEqual(result["records"][0]["source"],b.name)
            self.assertEqual(scan(out)["records"][0]["payload_sha256"],scan(b)["records"][0]["payload_sha256"])
            self.assertEqual(before,(a.read_bytes(),b.read_bytes()))
            self.assertFalse(result["source_plugins_disabled"])
    def test_reject(self):
        with TemporaryDirectory() as d:
            p=Path(d);a=p/"Base.esm";make(a)
            with self.assertRaises(ValueError):build_gmst_patch([a],p/"Patch.esp",a.name,[0x801])
            self.assertFalse((p/"Patch.esp").exists())
