import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.architecture import Building,generate
from chimster.collision import ray_box
from chimster.worldspace import Terrain
from chimster.terrain_tiles import tile,edge
from chimster.world_chunks import build,load
class PipelineTests(unittest.TestCase):
    def test_building(self):
        m,boxes=generate(Building())
        self.assertEqual(len(m.faces),96)
        self.assertFalse(any(ray_box((4,-1,1),(0,1,0),b["min"],b["max"]) is not None and b["id"]!="north" for b in boxes))
    def test_seams(self):
        t=Terrain(tuple(tuple(float(x+y) for x in range(65)) for y in range(65)),1,0)
        a=tile(t,0,0,1);b=tile(t,1,0,8);c=tile(t,0,1,16)
        self.assertEqual(edge(a,0,32),edge(b,0,32))
        self.assertEqual(edge(a,1,32),edge(c,1,32))
        self.assertLess(len(b.faces),len(a.faces))
    def test_chunks(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"chunks";build([{"id":"a","x_m":-1,"y_m":0},{"id":"b","x_m":1000,"y_m":0}],p,128)
            r=load(p,-1,0,0);self.assertEqual([i["id"] for i in r["instances"]],["a"])
            self.assertEqual(r["total_chunks"],2)
            (p/"-1_0.json").write_text("[]")
            with self.assertRaises(ValueError):load(p,-1,0,0)
