import unittest
from chimster.navmesh_collision import generate_collision
from chimster.navmesh_tiles import build
from chimster.navmesh_simplify import simplify
from chimster.navmesh import route,remove_triangles

class TiledNavigationTests(unittest.TestCase):
    def source(self):
        return {"schema":1,"spacing":1,"vertices":[],"triangles":[],
                "agent":{"radius":0,"height":1.8,"max_step":.4,"max_slope":45}}
    def quad(self,s,points):
        i=len(s["vertices"]);s["vertices"].extend(points)
        s["triangles"].extend([(i,i+1,i+2),(i,i+2,i+3)])
    def floor(self,s,a,b,c,d,z):
        self.quad(s,[(a,c,z),(b,c,z),(b,d,z),(a,d,z)])
    def geometry(self,m):
        return {tuple(sorted(tuple(round(x,6) for x in m["vertices"][v]) for v in t)) for t in m["triangles"]}
    def test_full_tiled_equivalence_and_cache(self):
        s=self.source();self.floor(s,-16,32,-8,8,0)
        s["agent"]["radius"]=.25
        first=build(s,tile_cells=8);m=first["mesh"]
        self.assertEqual(self.geometry(m),self.geometry(generate_collision(s)))
        self.assertGreater(m["seam_edges"],0)
        self.assertEqual(len(m["regions"]),1)
        second=build(s,first["cache"],8)
        self.assertEqual(second["rebuilt"],[])
        self.assertEqual(second["mesh"],m)
        self.assertEqual(second["reused"],first["rebuilt"])
        # Editing one end affects its halo tiles, not the entire world.
        self.quad(s,[(28,-4,0),(28,4,0),(28,4,3),(28,-4,3)])
        third=build(s,second["cache"],8)
        self.assertTrue(third["reused"])
        self.assertTrue(third["rebuilt"])
        self.assertEqual(self.geometry(third["mesh"]),self.geometry(generate_collision(s)))
        self.assertNotEqual(third["mesh"]["triangles"],m["triangles"])
    def test_step_across_tile_seam(self):
        s=self.source();self.floor(s,0,8,0,8,0);self.floor(s,8,16,0,8,.25)
        self.quad(s,[(8,0,0),(8,8,0),(8,8,.25),(8,0,.25)])
        m=build(s,tile_cells=8)["mesh"]
        self.assertTrue(m["links"])
        cross=[l for l in m["links"] if m["triangle_tiles"][l["from"]]!=m["triangle_tiles"][l["to"]]]
        self.assertTrue(cross)
        a,b=cross[0]["from"],cross[0]["to"]
        self.assertTrue(route(m,a,b,m["links"])["reachable"])
        self.assertFalse(route(m,a,b,m["links"],[l["id"] for l in cross])["reachable"])
        reduced=simplify(m)
        self.assertEqual(len(reduced["triangle_tiles"]),len(reduced["triangles"]))
        self.assertEqual([l["id"] for l in reduced["links"]],[l["id"] for l in m["links"]])
    def test_short_wall_is_not_a_supported_stair(self):
        s=self.source();self.floor(s,0,6,0,4,0)
        self.quad(s,[(3,0,0),(3,4,0),(3,4,.25),(3,0,.25)])
        m=generate_collision(s)
        self.assertEqual(len(m["regions"]),2)
        self.assertEqual(m["links"],[])
    def test_settings_change_invalidates_tiles(self):
        s=self.source();self.floor(s,0,12,0,12,0)
        first=build(s,tile_cells=8)
        s["agent"]["height"]=2
        second=build(s,first["cache"],8)
        self.assertFalse(second["reused"])
        self.assertTrue(second["rebuilt"])
        self.assertNotEqual(first["cache"]["settings_hash"],second["cache"]["settings_hash"])
