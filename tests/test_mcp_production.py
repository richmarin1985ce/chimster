import json
import tempfile
import unittest
from pathlib import Path
from chimster.project import Project
from chimster.mcp_bridge import Bridge

class ProductionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.p=Project.create(self.root/"project","Demo","newvegas")
        self.b=Bridge(self.p,allow_create=True,allow_edit=True)
        self.addCleanup(self.b.jobs.close)

    def add(self,key,kind,name,data):
        path=self.root/name
        path.write_text(data,encoding="utf-8")
        self.p.add(key,kind,path,self.p.read()["revision"])

    def test_native_build_atomic(self):
        spec={"schema":1,"records":[{"type":"GLOB","id":"One","fields":{"kind":"f","value":1}}]}
        self.add("records","records","records.json",json.dumps(spec))
        args=dict(operation="native-build",id="records",output_id="gameplay",revision=1)
        readonly=Bridge(self.p)
        self.addCleanup(readonly.jobs.close)
        self.assertIsNone(readonly.production_preview(**args)["proposal_token"])
        self.assertNotIn("production_apply",readonly.registry)
        preview=self.b.production_preview(**args)
        self.assertEqual(self.p.read()["revision"],1)
        self.assertEqual({r["kind"] for r in preview["outputs"]},{"plugin","ledger"})
        after=self.b.production.apply(preview["proposal_token"])
        self.assertEqual(after["revision"],2)
        self.assertEqual({r["id"]:r["sha256"] for r in after["outputs"]},
                         {r["id"]:r["sha256"] for r in preview["outputs"]})
        self.assertTrue(self.p.verify()["valid"])
        self.b.creation.recover("undo",2)
        self.assertNotIn("gameplay",self.p.read()["artifacts"])
        self.assertNotIn("gameplay.ids",self.p.read()["artifacts"])

    def test_navmesh_stale_and_discard(self):
        spec={"schema":1,"spacing":1,"heights":[[0,0,0],[0,0,0],[0,0,0]],"agent":{"radius":0}}
        self.add("floor","other","floor.json",json.dumps(spec))
        args=dict(operation="navmesh",id="floor",output_id="nav",revision=1)
        q=self.b.production_preview(**args)
        self.assertEqual(q["summary"]["triangles"],8)
        self.b.production_discard()
        with self.assertRaises(ValueError):self.b.production.apply(q["proposal_token"])
        q=self.b.production_preview(**args)
        self.add("extra","other","extra.txt","new")
        with self.assertRaises(ValueError):self.b.production.apply(q["proposal_token"])
        self.assertNotIn("nav",self.p.read()["artifacts"])

    def test_mesh_preview(self):
        self.add("mesh","mesh","triangle.obj","v 0 0 0\nv 1 0 0\nv 0 0 1\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n")
        q=self.b.production_preview("mesh-preview",id="mesh",output_id="preview",revision=1)
        self.b.production.apply(q["proposal_token"])
        self.assertTrue(self.p.object("preview").read_bytes().startswith(bytes.fromhex("89504e470d0a1a0a")))
        self.assertIn("mesh",self.p.read()["artifacts"])

if __name__=="__main__":
    unittest.main()
