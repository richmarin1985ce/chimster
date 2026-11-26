import unittest,os
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.native_flora import material_images,two_sided,build_native_flora
from chimster.flora import Recipe,generate

class NativeFloraTests(unittest.TestCase):
    def test_textures(self):
        a=material_images(42,16)
        self.assertEqual(a,material_images(42,16))
        self.assertTrue(all(len(x)==16*16*4 for x in a))
        self.assertIn(0,a[2][3::4]);self.assertIn(255,a[2][3::4])
    def test_two_sided(self):
        m=generate(Recipe(),2);n=two_sided(m)
        self.assertEqual(len(n.faces),len(m.faces)+sum(mat.endswith("__cutout") for _,mat in m.faces))
        self.assertEqual(len(m.faces),176)
    @unittest.skipUnless(os.environ.get("CHIMSTER_NIFBRIDGE"),"compiled native backend")
    def test_native_package(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"flora"
            r=build_native_flora(Recipe(),"newvegas",p,os.environ["CHIMSTER_NIFBRIDGE"],size=32)
            self.assertEqual(len(r["lods"]),4)
            self.assertTrue(all((p/x["output"]).is_file() for x in r["lods"]))
            self.assertTrue((p/"textures/chimster/bark_n.dds").is_file())
