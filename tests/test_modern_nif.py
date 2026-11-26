import unittest,os
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.flora import generate,Recipe
from chimster.modern_nif import mesh_exchange,export,GAMES
class ModernNifTests(unittest.TestCase):
    def test_exchange(self):
        m=generate(Recipe(),2);s=mesh_exchange(m,{"bark__opaque":{"diffuse":"textures/chimster/bark.dds"}})
        self.assertTrue(s.startswith("CHIMSTER_MESH_1 2"))
        self.assertIn("textures\\\\chimster\\\\bark.dds",s)
        with self.assertRaises(ValueError):mesh_exchange(m,{"bark__opaque":{"diffuse":"../bad.dds"}})
    @unittest.skipUnless(os.environ.get("CHIMSTER_NIFBRIDGE"),"optional compiled native backend")
    def test_all_targets(self):
        m=generate(Recipe(),2)
        materials={"bark__opaque":{"diffuse":"textures/chimster/bark.dds","normal":"textures/chimster/bark_n.dds"},"leaves__cutout":{"diffuse":"textures/chimster/leaves.dds","cutout":True}}
        with TemporaryDirectory() as d:
            for game in sorted(GAMES):
                with self.subTest(game=game):
                    p=Path(d)/(game+".nif");r=export(m,game,p,os.environ["CHIMSTER_NIFBRIDGE"],materials)
                    self.assertEqual(r["triangles"],176)
                    self.assertGreater(p.stat().st_size,128)
