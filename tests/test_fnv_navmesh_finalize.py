import struct,unittest
from chimster.fnv_navmesh_finalize import finalize,read_grid,compare_grid
from chimster.fnv_navmesh import inspect
from chimster.fnv_navi import inspect as navi

class NativeNavigationFinalizationTests(unittest.TestCase):
    def mesh(self):
        return {"vertices":[(0,0,0),(4,0,0),(4,4,0),(0,4,0)],
                "triangles":[(0,1,2),(0,2,3)]}
    def fields(self,result):return [(k.encode(),bytes.fromhex(v)) for k,v in result["fields"]]
    def test_native_candidate(self):
        r=finalize(self.mesh(),0x800,12,divisor=2,count_width=2,
            doors=[{"reference":0x801,"triangle":1,"tail_hex":"0000"}],
            external=[{"triangle":0,"edge":0,"target":0x802,"target_triangle":2,"prefix_hex":"11223344"}],
            cover=[1])
        parts=self.fields(r);report,edges=inspect(parts)
        self.assertEqual(report["issues"],[])
        self.assertEqual(report["cover_triangles"],[1])
        self.assertEqual(report["flags"],[1,0x400])
        self.assertEqual(report["doors"][0]["raw_target"],0x801)
        self.assertEqual(report["external"][0]["raw_target"],0x802)
        self.assertTrue(compare_grid(parts,2)["exact_bytes"])
        self.assertEqual(read_grid(dict(parts)[b"NVGD"],2,2)["divisor"],2)
        self.assertIn("not a finalized playable",r["status"])
    def test_reject_unsafe_links_and_grid(self):
        mesh=self.mesh();mesh["links"]=[{"from":0,"to":1}]
        with self.assertRaises(ValueError):finalize(mesh,0x800,12,divisor=2,count_width=2)
        with self.assertRaises(ValueError):finalize(self.mesh(),0x800,12,divisor=2,count_width=2,
            external=[{"triangle":0,"edge":2,"target":0x802,"target_triangle":0,"prefix_hex":"00000000"}])
        result=finalize(self.mesh(),0x800,12,divisor=2,count_width=2)
        raw=dict(self.fields(result))[b"NVGD"]
        with self.assertRaises(ValueError):read_grid(raw[:-1],2,2)
        with self.assertRaises(ValueError):read_grid(raw+b"\0",2,2)
    def test_navi_prefix_and_opaque_suffix(self):
        parts=[(b"NVER",struct.pack("<I",12)),(b"NVMI",struct.pack("<4sIIhh",b"test",0x801,0x800,-2,3)+b"opaque"),
               (b"NVCI",b"unknown")]
        r,edges=navi(parts)
        self.assertEqual(r["entries"][0]["grid"],[-2,3])
        self.assertEqual(r["opaque"],[1,2])
        self.assertEqual(edges,[(1,4,("NAVM",)),(1,8,("CELL","WRLD"))])
        with self.assertRaises(ValueError):navi(parts+[parts[1]])
