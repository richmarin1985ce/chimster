import unittest
from chimster.asset_forge import Session
from chimster.asset_nif_import import parse_exchange
from chimster.flora import Mesh

def square():
    return Mesh([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],
                [(0,0),(1,0),(1,1),(0,1)],
                [((0,1,2),"a"),((0,2,3),"b")])

class TopologyTests(unittest.TestCase):
    def test_shared_edge_split(self):
        s=Session(square());s.split_edge(s.edges().index((0,2)))
        self.assertEqual(len(s.mesh.faces),4)
        self.assertEqual(s.mesh.vertices[-1],(.5,.5,0))
        self.assertEqual(s.mesh.uv[-1],(.5,.5))
        self.assertEqual([m for _,m in s.mesh.faces],["a","a","b","b"])
        s.undo();self.assertEqual(s.mesh,square())
    def test_select_and_move(self):
        s=Session(square());s.move_selection("face",[0],(0,0,1))
        self.assertEqual(s.mesh.vertices[:3],[(0,0,1),(1,0,1),(1,1,1)])
        s.undo()
        with self.assertRaises(ValueError):s.move_selection("vertex",[0],(1,0,0))
        self.assertEqual(s.mesh,square())
    def test_delete_compact_and_materials(self):
        s=Session(square());s.bind("a","textures/a.dds")
        s.delete_faces([0])
        self.assertEqual(s.mesh.faces,[((0,1,2),"b")])
        self.assertEqual(len(s.mesh.vertices),3)
        self.assertEqual(s.materials,{})
        with self.assertRaises(ValueError):s.delete_faces([0])
        self.assertEqual(len(s.mesh.faces),1)
    def test_assign(self):
        s=Session(square());s.assign_faces([0],"b")
        self.assertEqual(s.groups(),["b"])
        s.undo();self.assertEqual(s.groups(),["a","b"])
    def test_native_exchange(self):
        data='CHIMSTER_IMPORT_1 1\nshape_0 "textures/a.dds" "" 1 3 1\n0 0 0 0 0\n1 0 0 1 0\n0 1 0 0 1\n0 1 2\n'
        s=parse_exchange(data)
        self.assertEqual(s.mesh.faces,[((0,1,2),"shape_0")])
        self.assertEqual(s.materials["shape_0"]["diffuse"],"textures\\a.dds")
        self.assertTrue(s.materials["shape_0"]["cutout"])
        for bad in (data.replace("0 1 2","0 1 3"),data.replace("0 0 0 0 0","nan 0 0 0 0"),data+"trailing",data.replace("textures/a.dds","../a.dds")):
            with self.assertRaises(ValueError):parse_exchange(bad)
