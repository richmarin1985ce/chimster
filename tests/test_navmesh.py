import unittest,struct
from chimster.navmesh import generate,topology,route,quality,remove_triangles
from chimster.navmesh_rooms import build
from chimster.fnv_navmesh import draft,inspect

class NavigationTests(unittest.TestCase):
    def test_clearance_and_topology(self):
        spec={"schema":1,"spacing":1,"heights":[[0]*11 for _ in range(11)],
              "agent":{"radius":.25,"height":1.8,"max_step":.4,"max_slope":45}}
        mesh=generate(spec)
        self.assertEqual(mesh["walkable_cells"],64)
        self.assertEqual(len(mesh["triangles"]),128)
        self.assertEqual(len(mesh["regions"]),1)
        self.assertTrue(route(mesh,0,127)["reachable"])
        spec["blocked"]=[[5,y] for y in range(10)]
        split=generate(spec)
        self.assertEqual(len(split["regions"]),2)
        self.assertFalse(route(split,split["regions"][0][0],split["regions"][1][0])["reachable"])
        spec["ceilings"]=[[1.0]*10 for _ in range(10)]
        self.assertTrue(quality(generate(spec))["empty"])
    def test_obstacle_and_slope(self):
        spec={"schema":1,"spacing":1,"heights":[[0,2,2],[0,2,2],[0,2,2]],
              "agent":{"radius":0,"height":1,"max_step":.5,"max_slope":45}}
        mesh=generate(spec)
        self.assertEqual(mesh["walkable_cells"],2)
        spec["obstacles"]=[{"min":[1,0,2.1],"max":[2,2,4]}]
        self.assertEqual(generate(spec)["walkable_cells"],0)
    def test_portal_route(self):
        layout={"schema":1,"rooms":[{"id":"A","min":[0,0,0],"max":[4,4,4]},
                    {"id":"B","min":[4,0,0],"max":[8,4,4]}],
                "portals":[{"id":"Door","rooms":["A","B"],"corners":[[4,1,0],[4,3,0],[4,3,3],[4,1,3]]}]}
        mesh=build(layout,.5,{"radius":.3,"height":1.8})
        self.assertEqual(len(mesh["regions"]),2)
        self.assertEqual(len(mesh["links"]),1)
        link=mesh["links"][0]
        self.assertTrue(route(mesh,link["from"],link["to"],mesh["links"])["reachable"])
        self.assertFalse(route(mesh,link["from"],link["to"],mesh["links"],["Door"])["reachable"])
        with self.assertRaises(ValueError):remove_triangles(mesh,[link["from"]])
    def test_native_draft(self):
        mesh=generate({"schema":1,"spacing":1,"heights":[[0,0],[0,0]],"agent":{"radius":0}})
        parts=draft(mesh,0x800,12)
        report,edges=inspect(parts)
        self.assertEqual(report["triangles"],mesh["triangles"])
        self.assertEqual(report["issues"],[])
        self.assertEqual(edges,[(1,0,("CELL",))])
        wrong=list(parts);wrong[1]=(b"DATA",struct.pack("<6I",0x800,3,2,0,0,0))
        with self.assertRaises(ValueError):inspect(wrong)
    def test_invalid_topology(self):
        vertices=[(0,0,0),(1,0,0),(0,1,0)]
        with self.assertRaises(ValueError):topology(vertices,[(0,1,2),(0,1,2)])
        with self.assertRaises(ValueError):topology(vertices,[(0,2,1)])
