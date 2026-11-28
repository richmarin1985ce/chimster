import itertools,struct,unittest
from chimster.collision_hull import hull
from chimster.fnv_navmesh_finalize import finalize
from chimster.fnv_navmesh_review import review,registration_manifest

class CollisionAndRegistrationTests(unittest.TestCase):
    def test_convex_core(self):
        points=list(itertools.product((0,1),repeat=3))+[(.5,.5,.5),(.5,0,0)]
        v,t=hull(points)
        self.assertEqual(len(t),12)
        self.assertEqual(len(hull([(0,0,0),(1,0,0),(0,1,0),(0,0,1)])[1]),4)
        with self.assertRaises(ValueError):hull([(0,0,0),(1,0,0),(1,1,0),(0,1,0)])
    def pair(self,shift=0):
        a={"vertices":[(0,0,0),(1,0,0),(1,1,0)],"triangles":[(0,1,2)]}
        b={"vertices":[(1+shift,0,0),(2+shift,0,0),(1+shift,1,0)],"triangles":[(0,1,2)]}
        x=finalize(a,0x800,12,divisor=1,count_width=2,
                   external=[{"triangle":0,"edge":1,"target":0x902,"target_triangle":0,"prefix_hex":"00000000"}])
        y=finalize(b,0x801,12,divisor=1,count_width=2,
                   external=[{"triangle":0,"edge":2,"target":0x901,"target_triangle":0,"prefix_hex":"00000000"}])
        rows=[{"form_id":0x901,**x},{"form_id":0x902,**y}]
        navi={"fields":[["NVER",struct.pack("<I",12).hex()]]+
               [["NVMI",(struct.pack("<4sIIhh",b"test",m,c,0,0)+b"opaque").hex()] for m,c in ((0x901,0x800),(0x902,0x801))]}
        return rows,navi
    def test_registration_and_seam_review(self):
        rows,navi=self.pair()
        r=review(rows,navi)
        self.assertTrue(r["valid_known_fields"],r["issues"])
        self.assertEqual(r["registered"],2)
        self.assertEqual(len(registration_manifest(rows)["registrations"]),2)
        rows,navi=self.pair(.1)
        self.assertIn("external-seam-mismatch",{i["code"] for i in review(rows,navi)["issues"]})
        navi["fields"].pop()
        self.assertIn("navi-registration-missing",{i["code"] for i in review(rows,navi)["issues"]})
