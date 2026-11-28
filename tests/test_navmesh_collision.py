import unittest
from chimster.navmesh_collision import generate_collision,union_area
from chimster.navmesh import route,remove_triangles

class CollisionAutoNavTests(unittest.TestCase):
    def source(self,radius=0):
        return {"schema":1,"spacing":1,"vertices":[],"triangles":[],
                "agent":{"radius":radius,"height":1.8,"max_slope":45,"max_step":.4}}
    def quad(self,s,points,reverse=False):
        i=len(s["vertices"]);s["vertices"].extend(points)
        rows=[(i,i+1,i+2),(i,i+2,i+3)]
        s["triangles"].extend([tuple(reversed(t)) for t in rows] if reverse else rows)
    def floor(self,s,x0,x1,y0,y1,z):
        self.quad(s,[(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)])
    def test_stacked_floors_and_clearance(self):
        s=self.source();self.floor(s,0,4,0,4,0);self.floor(s,0,4,0,4,3)
        m=generate_collision(s)
        self.assertEqual(m["walkable_cells"],32)
        self.assertEqual(len(m["regions"]),2)
        self.assertFalse(route(m,m["regions"][0][0],m["regions"][1][0],m["links"])["reachable"])
        self.assertEqual(set(m["triangle_layers"]),{0,1})
        updated=remove_triangles(m,[0])
        self.assertEqual(len(updated["triangle_layers"]),len(updated["triangles"]))
        s["agent"]["height"]=3.1
        self.assertEqual(generate_collision(s)["walkable_cells"],16)
    def test_step_and_wall(self):
        s=self.source();self.floor(s,0,2,0,2,0);self.floor(s,2,4,0,2,.25)
        self.quad(s,[(2,0,0),(2,2,0),(2,2,.25),(2,0,.25)])
        m=generate_collision(s)
        self.assertEqual(m["walkable_cells"],8)
        self.assertEqual(len(m["links"]),2)
        self.assertTrue(route(m,m["regions"][0][0],m["regions"][1][0],m["links"])["reachable"])
        s["agent"]["max_step"]=.1
        self.assertEqual(generate_collision(s)["links"],[])
        wall=self.source();self.floor(wall,0,4,0,4,0)
        self.quad(wall,[(2,0,0),(2,4,0),(2,4,3),(2,0,3)])
        m=generate_collision(wall)
        self.assertEqual(len(m["regions"]),2)
    def test_ramp_bridge_and_duplicate_coverage(self):
        s=self.source()
        self.quad(s,[(0,0,0),(4,0,1),(4,2,1),(0,2,0)])
        self.assertEqual(generate_collision(s)["walkable_cells"],8)
        s["agent"]["max_slope"]=5
        self.assertEqual(generate_collision(s)["walkable_cells"],0)
        gap=self.source();self.floor(gap,0,1,0,2,0);self.floor(gap,2,3,0,2,0)
        m=generate_collision(gap);self.assertEqual(len(m["regions"]),2);self.assertEqual(m["links"],[])
        partial=self.source()
        partial["vertices"]=[(0,0,0),(1,0,0),(0,1,0)]
        partial["triangles"]=[(0,1,2),(0,1,2)]
        self.assertEqual(generate_collision(partial)["walkable_cells"],0)
    def test_radius_erodes_edges(self):
        s=self.source(.2);self.floor(s,0,4,0,4,0)
        self.assertEqual(generate_collision(s)["walkable_cells"],4)

    def test_simplification_preserves_boundaries_and_links(self):
        from chimster.navmesh_simplify import simplify
        from chimster.navmesh import quality
        s=self.source();self.floor(s,0,6,0,6,0)
        original=generate_collision(s);reduced=simplify(original)
        self.assertLess(len(reduced["triangles"]),len(original["triangles"]))
        self.assertEqual(reduced["boundary"],original["boundary"])
        self.assertAlmostEqual(quality(original)["surface_area"],quality(reduced)["surface_area"])
        self.assertEqual(len(reduced["regions"]),1)
        s=self.source();self.floor(s,0,3,0,3,0);self.floor(s,3,6,0,3,.25)
        m=generate_collision(s);r=simplify(m)
        self.assertEqual([l["id"] for l in r["links"]],[l["id"] for l in m["links"]])
        self.assertTrue(all(l["clearance_checked"] for l in r["links"]))
        self.assertTrue(route(r,r["links"][0]["from"],r["links"][0]["to"],r["links"])["reachable"])

    def test_step_clearance_and_multi_riser(self):
        s=self.source()
        for i in range(4):
            self.floor(s,i,i+1,0,2,.2*i)
            if i:self.quad(s,[(i,0,.2*(i-1)),(i,2,.2*(i-1)),(i,2,.2*i),(i,0,.2*i)])
        m=generate_collision(s)
        self.assertEqual(len(m["links"]),6)
        self.assertTrue(route(m,m["regions"][0][0],m["regions"][-1][0],m["links"])["reachable"])
        s["agent"]["max_step"]=.1
        self.assertEqual(generate_collision(s)["links"],[])
