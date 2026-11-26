import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.flora import Recipe,generate
from chimster.lod import bake,atlas_billboard,terrain_grid,tile_groups,build_key,dirty_tiles,benchmark,build_tree
class LodTests(unittest.TestCase):
    def test_bake(self):
        m=generate(Recipe())
        a,info=bake(m,size=32)
        self.assertEqual(a,bake(m,size=32)[0])
        self.assertGreater(info["coverage"],0)
        self.assertLess(info["coverage"],1)
    def test_atlas(self):
        m,rgba,side,layout=atlas_billboard(generate(Recipe()),2,32)
        self.assertEqual(len(m.faces),4)
        self.assertEqual(len(layout),2)
        self.assertEqual(len(rgba),side*side*4)
        self.assertTrue(all(0<=u<=1 and 0<=v<=1 for u,v in m.uv))
    def test_terrain(self):
        h=[[x+y for x in range(5)] for y in range(5)]
        fine=terrain_grid(h);coarse=terrain_grid(h,2)
        self.assertEqual(len(fine.faces),32)
        self.assertEqual(len(coarse.faces),8)
        self.assertEqual(fine.vertices[-1],coarse.vertices[-1])
    def test_tiles(self):
        rows=tile_groups([{"x":-1,"y":0,"kind":"tree","material_set":"a","id":"t"},{"x":-1,"y":0,"kind":"object","material_set":"a","id":"o"}],32)
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]["tile"],[-1,0])
    def test_key(self):
        self.assertEqual(build_key({"a":1,"b":2}),build_key({"b":2,"a":1}))
        self.assertEqual(dirty_tiles({"a":"1","b":"2"},{"a":"1","c":"3"}),["b","c"])
    def test_benchmark(self):
        report=benchmark(2,32)
        self.assertEqual(report["triangles"],[1960,792,352,8])
        self.assertGreater(report["unique_bakes"],0)
    def test_build(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"out";r=build_tree(Recipe(),p,32)
            self.assertTrue((p/"tree_atlas.png").exists())
            self.assertIn("mtllib tree_atlas.mtl",(p/"tree_lod3.obj").read_text())
            self.assertEqual(r["lods"][-1]["triangles"],4)
