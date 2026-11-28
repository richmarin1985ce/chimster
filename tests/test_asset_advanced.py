import unittest
from chimster.flora import Mesh
from chimster.asset_forge import Session

def square():
    return Mesh([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[(0,0),(1,0),(1,1),(0,1)],[((0,1,2),"a"),((0,2,3),"a")])

class AdvancedAssetTests(unittest.TestCase):
    def test_region_extrude_and_redo(self):
        s=Session(square());s.extrude_faces([0,1],(0,0,1))
        self.assertEqual(len(s.mesh.faces),10)
        self.assertEqual(len(s.mesh.vertices),8)
        self.assertEqual(sum(v[2]==1 for v in s.mesh.vertices),4)
        s.undo();self.assertEqual(s.mesh,square())
        s.redo();self.assertEqual(len(s.mesh.faces),10)
        s.undo();s.move_selection("vertex",[0],(0,0,1));s.redo()
        self.assertEqual(len(s.mesh.faces),2)
    def test_reject_parallel_extrusion(self):
        s=Session(square())
        with self.assertRaises(ValueError):s.extrude_faces([0,1],(1,0,0))
        self.assertEqual(s.mesh,square())
    def test_uv_projection_preserves_unselected_face(self):
        s=Session(square());s.project_uv([0],"XY")
        self.assertEqual(s.mesh.faces[1],((0,2,3),"a"))
        self.assertEqual(s.mesh.uv[:4],square().uv)
        self.assertEqual(len(s.mesh.vertices),6)
        s.transform_uv("face",[0],(2,2),(.5,.5))
        self.assertEqual(s.mesh.uv[:4],square().uv)
        s.undo();s.undo();self.assertEqual(s.mesh,square())
    def test_weld_seams(self):
        m=square();m.vertices.append(m.vertices[0]);m.uv.append(m.uv[0])
        m.faces[1]=((4,2,3),"a")
        s=Session(m);s.weld_vertices([0,4],0)
        self.assertEqual(s.mesh,square())
        s.undo();self.assertEqual(s.mesh,m)
        m.uv[4]=(.1,.2);s=Session(m)
        with self.assertRaises(ValueError):s.weld_vertices([0,4],0)
        self.assertEqual(s.mesh,m)
    def test_project_roundtrip(self):
        import tempfile
        from pathlib import Path
        from chimster.asset_project import save,load
        s=Session(square());s.bind("a","textures/a.dds")
        s.extrude_faces([0,1],(0,0,1))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"test.casset"
            save(s,p);restored=load(p)
            self.assertEqual(restored.mesh,s.mesh)
            self.assertEqual(restored.materials,s.materials)
            with self.assertRaises(FileExistsError):save(s,p)
