import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.integrations import texconv,caprica,champollion,spriggit,bsarch
from chimster.deploy import stage_overlay
class QuickIntegrationTests(unittest.TestCase):
    def test_plans(self):
        with TemporaryDirectory() as d:
            p=Path(d);e=p/"tool.exe";e.touch()
            for name in ("a.png","a.psc","a.pex","flags.flg","a.esp"):(p/name).touch()
            (p/"data").mkdir()
            self.assertIn("BC3_UNORM",texconv(e,p/"a.png",p/"dds")["args"])
            self.assertIn("skyrim",caprica(e,p/"a.psc",p/"pex","skyrim",[p/"data"],p/"flags.flg")["args"])
            self.assertIn("-p",champollion(e,p/"a.pex",p/"psc")["args"])
            self.assertIn("serialize",spriggit(e,p/"a.esp",p/"yaml","SkyrimSE")["args"])
            self.assertIn("-fnv",bsarch(e,p/"data",p/"new.bsa","newvegas")["args"])
            with self.assertRaises(ValueError):bsarch(e,p/"data",p/"data/new.bsa","newvegas")
    def test_overlay(self):
        with TemporaryDirectory() as d:
            p=Path(d);a=p/"a";b=p/"b";a.mkdir();b.mkdir()
            (a/"Tree.NIF").write_bytes(b"a");(b/"tree.nif").write_bytes(b"b")
            r=stage_overlay([a,b],p/"stage")
            self.assertEqual((p/"stage/tree.nif").read_bytes(),b"b")
            self.assertEqual(len(r["conflicts"]),1)
            self.assertEqual((a/"Tree.NIF").read_bytes(),b"a")
