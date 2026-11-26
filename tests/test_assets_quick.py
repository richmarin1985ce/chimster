import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.atlas import Tile,pack,remap_uv,write_png
from chimster.validation import index_assets,audit_assets
from chimster.fomod import write_fomod
class AssetQuickTests(unittest.TestCase):
    def test_atlas(self):
        t=Tile("leaf",1,1,b"\xff\x00\x00\xff")
        pix,layout=pack([t],8,8,1)
        self.assertEqual(pix[:4],t.rgba)
        self.assertEqual(remap_uv(0,0,layout["leaf"]),(1/8,1/8))
        with TemporaryDirectory() as d:
            p=Path(d)/"atlas.png";write_png(p,8,8,pix)
            self.assertEqual(p.read_bytes()[:8],b"\x89PNG\r\n\x1a\n")
    def test_overlay(self):
        with TemporaryDirectory() as d:
            a=Path(d)/"a";b=Path(d)/"b";a.mkdir();b.mkdir()
            (a/"Tree.nif").touch();(b/"tree.nif").touch()
            rows=audit_assets(index_assets([a,b]),[{"owner":"Tree","path":"TREE.NIF"},{"owner":"Other","path":"none.nif"}])
            self.assertEqual(rows[0]["winner"],str((b/"tree.nif").resolve()))
            self.assertEqual(rows[1]["status"],"missing-loose-file")
    def test_fomod(self):
        with TemporaryDirectory() as d:
            p=Path(d);(p/"Example.esp").touch()
            f=write_fomod(p,"Example","Author","1.0",["Example.esp"])
            self.assertIn("Example.esp",(f/"ModuleConfig.xml").read_text())
