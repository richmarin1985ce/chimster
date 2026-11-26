import unittest
from chimster.spatial import Entry,build,query
from chimster.gpu_viewport import basis,Settings,visible
from chimster.scene import Camera
class SpatialTests(unittest.TestCase):
    def test_equivalence(self):
        entries=[Entry(i,None,(float(i%20)*20-200,float(i//20)*20-200,0),2) for i in range(400)]
        view=basis(Camera(),640,480,Settings())
        pred=lambda c,r:visible(c,r,view,Settings())
        got,stats=query(build(entries,8),pred)
        self.assertEqual(got,[e for e in entries if pred(e.center,e.radius)])
        self.assertGreater(stats["chunks_rejected"],0)
        self.assertLess(stats["objects_tested"],len(entries))
    def test_empty(self):
        self.assertEqual(query(build([]),lambda c,r:True)[0],[])
