import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from chimster.asset_forge import Session
from chimster.flora import Mesh, Recipe, generate
from chimster.rock_gen import RockRecipe, generate as rock
from chimster.architecture import Building, generate as building
from chimster.scene import load_obj

class AssetForgeTests(unittest.TestCase):
    def test_existing_sources(self):
        for mesh in (generate(Recipe()),rock(RockRecipe()),building(Building())[0]):
            self.assertEqual(Session(mesh).report()["triangles"],len(mesh.faces))
    def test_transform_undo(self):
        m=Mesh([(1,0,2),(2,0,2),(1,1,3)],[(0,0),(1,0),(0,1)],[((0,1,2),"wall")])
        s=Session(m)
        s.transform(2,90,True)
        for a,b in zip(s.mesh.vertices[0],(0,2,0)):self.assertAlmostEqual(a,b)
        self.assertEqual(s.mesh.faces,m.faces)
        s.undo()
        self.assertEqual(s.mesh,m)
        with self.assertRaises(ValueError):s.transform(float("nan"))
        self.assertEqual(s.mesh,m)
    def test_material_and_native_routing(self):
        s=Session(rock(RockRecipe()))
        group=s.groups()[0]
        s.bind(group,"textures/rock.dds","textures/rock_n.dds")
        with self.assertRaises(ValueError):s.bind(group,"../rock.dds")
        with self.assertRaises(ValueError):s.export_nif("out.nif","morrowind",1)
        with self.assertRaises(ValueError):s.export_nif("out.nif","newvegas",1)
        with patch("chimster.modern_nif.export",return_value={"status":"mock"}) as export:
            s.export_nif("out.nif","newvegas",2,"helper",True)
            self.assertEqual(export.call_args.args[4][group]["diffuse"],"textures\\rock.dds")
            self.assertEqual(export.call_args.args[5:],(2,True))
        s.undo()
        self.assertEqual(s.materials,{})
    def test_obj_roundtrip(self):
        s=Session(rock(RockRecipe()))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"mesh.obj"
            s.export_obj(p)
            self.assertEqual(load_obj(p).stats(),s.mesh.stats())
            with self.assertRaises(FileExistsError):s.export_obj(p)
    def test_invalid_material(self):
        m=rock(RockRecipe());m.faces[0]=(m.faces[0][0],"bad\nname")
        with self.assertRaises(ValueError):Session(m)

if __name__=="__main__":unittest.main()
