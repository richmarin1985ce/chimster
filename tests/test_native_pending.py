import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
from chimster.fo4_collision import mesh_from_body
from chimster.fnv_portal_fields import inspect

class PendingNativeTests(unittest.TestCase):
    def body(self):
        return NS(body_index=0,physics=NS(is_dynamic=False,trigger=False,motion_id=0x7fffffff),
                  shape_type="compressed_mesh",transform=None,children=[],
                  verts=[(0,0,0),(1,0,0),(0,1,0)],faces=[(0,1,2)],capsule_ends=None)
    def test_static_body(self):
        shape=self.body()
        result=mesh_from_body([shape],0,10)
        self.assertEqual(result["vertices"],[(0,0,0),(10,0,0),(0,10,0)])
        self.assertEqual(result["triangles"],[(0,1,2)])
    def test_reject_dynamic_and_incomplete(self):
        shape=self.body();shape.physics.is_dynamic=True
        with self.assertRaises(ValueError):mesh_from_body([shape],0,1)
        shape.physics.is_dynamic=False
        with self.assertRaises(ValueError):mesh_from_body([shape],1,1)
        shape.faces=[(0,1,3)]
        with self.assertRaises(ValueError):mesh_from_body([shape],0,1)
    def test_child_transform(self):
        root=self.body();child=self.body()
        root.shape_type="compound";root.children=[child]
        child.transform=NS(position=(1,2,0),rotation=((0,-1,0),(1,0,0),(0,0,1)),scale=1)
        self.assertEqual(mesh_from_body([root],0,1)["vertices"],[(1,2,0),(1,3,0),(0,2,0)])
    def test_xndp_signed_triangle(self):
        row,edges=inspect([(b"XNDP",struct.pack("<Ih2s",0x800,12,b"ab"))])
        self.assertEqual(row["navigation_door"]["triangle"],12)
        self.assertEqual(row["navigation_door"]["tail_hex"],"6162")
        self.assertEqual(edges,[(0,0,("NAVM",))])
    def test_native_interior_stage(self):
        from chimster.fnv_interior import export
        from chimster.fnv_records import scan
        from chimster.world_validator import validate
        spec={"schema":1,"cells":[{"id":"NavCell","title":"Navigation test",
             "layout":{"schema":1,"rooms":[{"id":"Room","min":[0,0,0],"max":[8,8,4]}]},
             "navmesh_stage":{"version":12,"divisor":2,"count_width":2,
             "mesh":{"vertices":[[0,0,0],[4,0,0],[4,4,0],[0,4,0]],"triangles":[[0,1,2],[0,2,3]]}}}]}
        with TemporaryDirectory() as d:
            p=Path(d)/"Stage.esp";result=export(spec,p)
            self.assertIn("UNFINALIZED",result["navigation_status"])
            self.assertEqual(len(result["navigation_manifest"]),1)
            self.assertEqual({r["signature"] for r in scan(p)["records"]},{"CELL","NAVM"})
            self.assertEqual(validate([p],navmesh=True)["navmesh_records"],1)
