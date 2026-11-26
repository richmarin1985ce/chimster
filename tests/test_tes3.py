import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.tes3 import Record,sub,records,inventory,write_static_override,field
class TES3Tests(unittest.TestCase):
    def test_write_override(self):
        with TemporaryDirectory() as d:
            root=Path(d);base=root/"Base.esm";out=root/"Patch.esp"
            raw=Record("TES3",0,0,sub(b"HEDR",struct.pack("<fI32s256sI",1.3,1,b"",b"",1))).encode()+Record("STAT",0,0,sub(b"NAME",b"TreeA\0")+sub(b"MODL",b"old.nif\0")).encode()
            base.write_bytes(raw)
            write_static_override(base,out,"treea","flora/new.nif")
            self.assertEqual(base.read_bytes(),raw)
            self.assertEqual(field(list(records(out))[1],b"MODL"),b"flora\\new.nif\0")
            self.assertEqual(inventory(out)[0]["id"],"TreeA")
            with self.assertRaises(FileExistsError):write_static_override(base,out,"treea","flora/new.nif")
    def test_truncated(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"bad.esp";p.write_bytes(b"TES3")
            with self.assertRaises(ValueError):list(records(p))
