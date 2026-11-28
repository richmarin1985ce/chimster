import unittest
from chimster.navmesh import generate,route,quality
from chimster.navmesh_areas import classify,paint
from chimster.navmesh_adaptive import refine
from chimster.navmesh_simplify import simplify

class AdaptiveNavTests(unittest.TestCase):
    def source(self):
        return {"schema":1,"spacing":1,"vertices":[(0,0,0),(8,0,0),(8,8,0),(0,8,0)],
                "triangles":[(0,1,2),(0,2,3)],"agent":{"radius":0,"height":1.8}}
    def test_resolution_budget(self):
        bundle=refine(self.source(),levels=3,tile_cells=8,triangle_budget=600)
        self.assertEqual(bundle["spacing"],.5)
        self.assertEqual(bundle["refinement"]["attempts"][-1]["status"],"triangle-budget")
        self.assertAlmostEqual(quality(bundle["mesh"])["surface_area"],64.)
        self.assertEqual(len(bundle["mesh"]["regions"]),1)
        self.assertEqual(len(bundle["mesh"]["triangle_areas"]),len(bundle["mesh"]["triangles"]))
    def test_cost_and_exclusion(self):
        mesh=classify(generate({"schema":1,"spacing":1,"heights":[[0]*5 for _ in range(5)],"agent":{"radius":0}}),
                      {"costs":{"hazard":20}})
        mesh=paint(mesh,[0,1],"hazard")
        self.assertFalse(route(mesh,0,31,avoid=["hazard"])["reachable"])
        self.assertGreater(route(mesh,0,31)["cost"],route(mesh,0,31,cost_overrides={"hazard":1})["cost"])
        original=list(mesh["triangle_areas"])
        with self.assertRaises(ValueError):paint(mesh,[999],"ground")
        self.assertEqual(mesh["triangle_areas"],original)
        reduced=simplify(mesh)
        self.assertEqual(len(reduced["triangle_areas"]),len(reduced["triangles"]))
        self.assertIn("hazard",reduced["triangle_areas"])
    def test_concave_fan(self):
        # Star-shaped concave polygon around a strictly interior vertex.
        vertices=[(0,0,0),(4,0,0),(4,4,0),(2,2.5,0),(0,4,0),(2,1,0)]
        triangles=[(5,i,(i+1)%5) for i in range(5)]
        from chimster.navmesh import topology
        mesh={"vertices":vertices,"triangles":triangles,**topology(vertices,triangles)}
        reduced=simplify(mesh)
        self.assertEqual(len(reduced["triangles"]),3)
        self.assertEqual(reduced["boundary"],mesh["boundary"])
        self.assertAlmostEqual(quality(mesh)["surface_area"],quality(reduced)["surface_area"])
