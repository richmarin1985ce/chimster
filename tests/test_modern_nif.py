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

    @unittest.skipUnless(os.environ.get("CHIMSTER_NIFBRIDGE"),"optional compiled native backend")
    def test_native_box_collision(self):
        m=generate(Recipe(),2)
        with TemporaryDirectory() as d:
            p=Path(d)/"box.nif"
            result=export(m,"newvegas",p,os.environ["CHIMSTER_NIFBRIDGE"],scale=10,box_collision=True)
            self.assertTrue(result["box_collision"])
            self.assertTrue(p.is_file())

    @unittest.skipUnless(os.environ.get("CHIMSTER_NIFBRIDGE"),"optional compiled native backend")
    def test_native_compound_collision(self):
        from chimster.architecture import Building,generate
        m,boxes=generate(Building())
        spec={"kind":"compound_aabb","list_material":"broken_concrete","boxes":boxes}
        with TemporaryDirectory() as d:
            for game in ("newvegas","fallout3"):
                with self.subTest(game=game):
                    p=Path(d)/(game+".nif")
                    result=export(m,game,p,os.environ["CHIMSTER_NIFBRIDGE"],scale=10,compound_collision=spec)
                    self.assertTrue(result["compound_collision"])
                    self.assertEqual(result["collision_boxes"],8)
                    self.assertEqual(result["collision_materials"],[9,17,0,0,0,0,0,0])
                    self.assertEqual(result["list_material"],19)
                    self.assertIn("warning",result)
                    self.assertTrue(p.is_file())
