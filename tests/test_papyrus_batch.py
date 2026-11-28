import unittest
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from chimster.papyrus_batch import plan, batch

class BatchTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.src=self.root/"src";self.src.mkdir()
        self.lib=self.root/"lib";self.lib.mkdir()
        self.tools=self.root/"tools";self.tools.mkdir()
        self.exe=self.tools/"compiler.exe";self.exe.write_bytes(b"fixture")
        self.flags=self.tools/"flags.flg";self.flags.write_text("fixture")
        self.out=self.root/"out"
        (self.lib/"Base.psc").write_text("Scriptname Base")
        (self.src/"A.psc").write_text("Scriptname A extends Base")
        (self.src/"B.psc").write_text("Scriptname B extends A\nImport Missing")
    def args(self):
        return ("skyrim","ck",self.exe,self.src,self.flags,[self.lib],self.out)
    def test_preview(self):
        p=plan(*self.args())
        self.assertEqual(p["order"],["a","b"])
        self.assertEqual(p["unresolved"],{"b":["missing"]})
        self.assertFalse(self.out.exists())
    def test_duplicate(self):
        (self.lib/"a.psc").write_text("Scriptname a")
        with self.assertRaises(ValueError):plan(*self.args())
    def test_inheritance_cycle(self):
        (self.src/"A.psc").write_text("Scriptname A extends B")
        with self.assertRaises(ValueError):plan(*self.args())
    def test_import_cycle(self):
        (self.src/"A.psc").write_text("Scriptname A\nImport B")
        (self.src/"B.psc").write_text("Scriptname B\nImport A")
        self.assertEqual(plan(*self.args())["import_cycle_or_blocked"],["a","b"])
    def mock_build(self,game,backend,exe,source,flags,imports,output,**kwargs):
        import hashlib
        output.mkdir()
        p=output/(source.stem+".pex")
        data=struct.pack(">IBBHQ",0xFA57C0DE,3,2,1,0)+b"\0\0"*4
        p.write_bytes(data)
        return {"status":"header-checked","artifact":{"sha256":hashlib.sha256(data).hexdigest()}}
    def test_success(self):
        with patch("chimster.papyrus_batch.build",side_effect=self.mock_build):
            r=batch(*self.args(),execute=True)
        self.assertEqual(r["status"],"header-checked")
        self.assertEqual({p.name for p in self.out.iterdir()},{"A.pex","B.pex","batch.json"})
    def test_failure_is_atomic(self):
        def fail(*args,**kwargs):
            if args[3].stem=="B":return {"status":"compiler-failed"}
            return self.mock_build(*args,**kwargs)
        with patch("chimster.papyrus_batch.build",side_effect=fail):
            r=batch(*self.args(),execute=True)
        self.assertEqual(r["status"],"batch-failed")
        self.assertFalse(self.out.exists())
    def test_input_change(self):
        def mutate(*args,**kwargs):
            if args[3].stem=="B":(self.lib/"Base.psc").write_text("Scriptname Base\n; changed")
            return self.mock_build(*args,**kwargs)
        with patch("chimster.papyrus_batch.build",side_effect=mutate):
            self.assertEqual(batch(*self.args(),execute=True)["status"],"inputs-changed")
        self.assertFalse(self.out.exists())
