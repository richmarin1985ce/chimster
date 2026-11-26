import os,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.flora import Recipe,generate
from chimster.nif_export import export_legacy
class NifTests(unittest.TestCase):
    def test_unsupported(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):export_legacy(generate(Recipe()),Path(d)/"tree.nif","starfield")
    @unittest.skipUnless(os.environ.get("CHIMSTER_TEST_PYFFI"),"optional PyFFI integration")
    def test_roundtrip(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"tree.nif"
            r=export_legacy(generate(Recipe(),2),p)
            self.assertEqual(r["triangles"],176)
            self.assertTrue(p.read_bytes().startswith(b"NetImmerse File Format"))
