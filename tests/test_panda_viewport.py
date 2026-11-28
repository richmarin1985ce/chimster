import importlib.util
import unittest
from math import inf
from chimster.panda_viewport import lod_ranges, texture_bytes, build_scene
from chimster.gpu_viewport import ImageMap, Material, Settings
from chimster.scene import Scene, Instance
from chimster.flora import Mesh

class PandaViewportTests(unittest.TestCase):
    def test_sparse_lod_ranges(self):
        self.assertEqual(lod_ranges([True,False,True,False],(10,20,30)),[(0,0,20),(2,20,inf)])
        self.assertEqual(lod_ranges([True,False,False,False],(10,20,30)),[(0,0,inf)])
        self.assertEqual(lod_ranges([True]*4,(10,20,30)),[(0,0,10),(1,10,20),(2,20,30),(3,30,inf)])
        with self.assertRaises(ValueError):
            lod_ranges([True]*4,(20,10,30))

    def test_texture_row_order(self):
        image=ImageMap(1,2,bytes((255,0,0,255,0,0,255,255)))
        self.assertEqual(texture_bytes(image),bytes((0,0,255,255,255,0,0,255)))

    @unittest.skipUnless(importlib.util.find_spec("panda3d"),"optional Panda3D dependency")
    def test_scene_graph_lod_and_material(self):
        from panda3d.core import AlphaTestAttrib
        m=Mesh([(0,0,0),(1,0,0),(0,1,0)],[(0,0),(1,0),(0,1)],[((0,1,2),"leaf")])
        scene=Scene({"tree":m,"tree@lod2":m},[Instance("one","tree",scale=2),Instance("two","tree")])
        mat=Material(diffuse=ImageMap(1,1,bytes((255,255,255,128))),cutout=.5)
        root=build_scene(scene,{"leaf":mat},Settings(lod_distances=(10,20,30)))
        try:
            first=root.find("one")
            self.assertEqual(first.get_tag("chimster_id"),"one")
            lod=first.find("distance-lod")
            self.assertEqual(lod.node().get_num_switches(),2)
            self.assertEqual(lod.node().get_in(0),20)
            self.assertEqual(lod.get_child(0).get_sx(),2)
            part=first.find("**/+GeomNode")
            self.assertFalse(part.is_empty())
            self.assertIsNotNone(part.get_attrib(AlphaTestAttrib))
            self.assertTrue(part.has_texture())
        finally:
            root.remove_node()
