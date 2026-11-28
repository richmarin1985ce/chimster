import struct,unittest
from chimster.fnv_navi_generate import connection,encode_connection,map_entry,extend
from chimster.fnv_navmesh_finalize import finalize
from chimster.fnv_navmesh import inspect
from chimster.fnv_navi import inspect as inspect_index
from chimster.collision_obstacles import normalize,overlaps
from chimster.navmesh_collision import generate_collision
from chimster.navmesh_tiles import build

class PendingNavTests(unittest.TestCase):
    def test_connections(self):
        raw=encode_connection(0x1000800,[0x1000802,0x1000801,0x1000802],[],[0x1000803])
        self.assertEqual(connection(raw),{"mesh":0x1000800,"standard":[0x1000801,0x1000802],"preferred":[],"doors":[0x1000803]})
        for bad in (raw[:-1],raw+b"\0",struct.pack("<IIII",0x800,0xffffffff,0,0)):
            with self.assertRaises(ValueError):connection(bad)

    def test_map_entry(self):
        b=map_entry(0x800,0x801,[(0,0,0),(6,0,0),(0,6,3)])
        self.assertEqual(len(b),32)
        self.assertEqual(struct.unpack("<IIIhh4f",b),(0,0x800,0x801,0,0,2.,2.,1.,0.))

    def pair(self,shift=0):
        def mesh(v,cell,edge,target):
            candidate=finalize({"vertices":v,"triangles":[(0,1,2)]},cell,12,divisor=1,count_width=2,
                               external=[{"triangle":0,"edge":edge,"target":target,"target_triangle":0,"prefix_hex":"00000000"}])
            return inspect([(k.encode(),bytes.fromhex(raw)) for k,raw in candidate["fields"]])[0]
        a=mesh([(0,0,0),(1,0,0),(1,1,0)],0x1000800,1,0x1000902)
        b=mesh([(1+shift,0,0),(2+shift,0,0),(1+shift,1,0)],0x1000801,2,0x1000901)
        return [(0x1000901,a),(0x1000902,b)]

    def test_extension_preserves_master(self):
        old=[(b"NVER",struct.pack("<I",12)),(b"NVMI",map_entry(0x800,0x801,[(0,0,0)])),(b"NVCI",encode_connection(0x800))]
        merged=extend(old,self.pair())
        self.assertEqual([t for t,_ in merged],[b"NVER"]+[b"NVMI"]*3+[b"NVCI"]*3)
        self.assertEqual([merged[0],merged[1],merged[4]],old)
        report,edges=inspect_index(merged)
        self.assertEqual(len(report["entries"]),3)
        self.assertEqual(report["connections"][1]["standard"],[0x1000902])
        self.assertEqual(report["connections"][2]["standard"],[0x1000901])
        with self.assertRaisesRegex(ValueError,"seam"):extend(old,self.pair(.1))

    def test_solids(self):
        b=normalize([{"min":[0,0,0],"max":[1,1,1]}])[0]
        self.assertTrue(overlaps(b,[.5,.5,.5],[2,2,2]))
        self.assertFalse(overlaps(b,[1,0,0],[2,1,1]))
        with self.assertRaises(ValueError):normalize([{"min":[0,0,0],"max":[1,0,1]}])
        with self.assertRaises(ValueError):normalize([{"min":[0,0,0],"max":[1,float("nan"),1]}])
        source={"schema":1,"spacing":1,"agent":{"radius":0},"vertices":[(0,0,0),(4,0,0),(4,4,0),(0,4,0)],"triangles":[(0,1,2),(0,2,3)]}
        baseline=build(source,tile_cells=8)
        source["solid_obstacles"]=[{"min":[1,1,-1],"max":[3,3,2]}]
        mesh=generate_collision(source)
        self.assertEqual(mesh["walkable_cells"],12)
        self.assertEqual(mesh["rejected"]["solid_obstacle"],4)
        tiled=build(source,baseline["cache"],8)
        self.assertTrue(tiled["rebuilt"])
        self.assertEqual(len(tiled["mesh"]["triangles"]),len(mesh["triangles"]))
