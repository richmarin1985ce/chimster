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
                    # Exercise the compiled reader as well as the writer on every supported stream.
                    import subprocess,shlex
                    read=subprocess.run([os.environ["CHIMSTER_NIFBRIDGE"],"extract-mesh",str(p)],
                                        capture_output=True,text=True,timeout=60)
                    self.assertEqual(read.returncode,0,read.stderr)
                    lines=iter(read.stdout.splitlines())
                    self.assertEqual(next(lines),"CHIMSTER_IMPORT_1 2")
                    triangle_count=0
                    cutouts=[]
                    for _ in range(2):
                        name,diffuse,normal,cut,nv,nt=shlex.split(next(lines))
                        self.assertTrue(name.startswith("shape_"))
                        cutouts.append(int(cut))
                        vertex_count=int(nv)
                        for _ in range(vertex_count):
                            self.assertEqual(len(next(lines).split()),5)
                        for _ in range(int(nt)):
                            indices=list(map(int,next(lines).split()))
                            self.assertEqual(len(set(indices)),3)
                            self.assertTrue(all(0<=i<vertex_count for i in indices))
                        triangle_count+=int(nt)
                    self.assertEqual(triangle_count,len(m.faces))
                    self.assertEqual(sorted(cutouts),[0,1])
                    self.assertIsNone(next(lines,None))

    @unittest.skipUnless(os.environ.get("CHIMSTER_NIFBRIDGE"),"optional compiled native backend")
    def test_native_box_collision(self):
        m=generate(Recipe(),2)
        with TemporaryDirectory() as d:
            p=Path(d)/"box.nif"
            result=export(m,"newvegas",p,os.environ["CHIMSTER_NIFBRIDGE"],scale=10,box_collision=True)
            self.assertTrue(result["box_collision"])
            self.assertTrue(p.is_file())
            from chimster.modern_nif import extract_collision
            collision=extract_collision(p,os.environ["CHIMSTER_NIFBRIDGE"],7)
            self.assertEqual(len(collision["vertices"]),8)
            self.assertEqual(len(collision["triangles"]),12)
            for axis in range(3):
                self.assertAlmostEqual(min(v[axis] for v in collision["vertices"]),10*min(v[axis] for v in m.vertices),places=4)
                self.assertAlmostEqual(max(v[axis] for v in collision["vertices"]),10*max(v[axis] for v in m.vertices),places=4)

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
                    from chimster.modern_nif import extract_collision
                    collision=extract_collision(p,os.environ["CHIMSTER_NIFBRIDGE"],7)
                    self.assertEqual(len(collision["vertices"]),8*8)
                    self.assertEqual(len(collision["triangles"]),8*12)
