import json
import tempfile
import unittest
from pathlib import Path
from chimster.project import Project
from chimster.worldspace import Terrain
from chimster.fnv_world import build
from chimster.mcp_bridge import Bridge
from chimster.mcp_operations import inspect_record

class NativeMCPTests(unittest.TestCase):
    def test_preview_apply_undo(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=Project.create(root/"project","Demo","newvegas")
            src=root/"World.esp"
            t=Terrain(tuple(tuple(0. for _ in range(33)) for _ in range(33)))
            build(t,src,title="Old")
            original=src.read_bytes()
            p.add("world","plugin",src,0)
            a=p.read()["artifacts"]["world"]
            r=inspect_record(p,"world",src.name,0x800)["record"]
            args=dict(id="world",origin=src.name,local_id=0x800,field="FULL",
                      value_json=json.dumps("New"),revision=1,plugin_sha256=a["sha256"],
                      record_sha256=r["payload_sha256"])
            readonly=Bridge(p)
            self.addCleanup(readonly.jobs.close)
            self.assertIsNone(readonly.native.preview(**args)["proposal_token"])
            self.assertNotIn("fnv_record_apply_edit",readonly.registry)
            with self.assertRaises(ValueError):
                Bridge(p,allow_native=True)
            b=Bridge(p,allow_edit=True,allow_native=True)
            self.addCleanup(b.jobs.close)
            preview=b.native.preview(**args)
            self.assertEqual(preview["after"],"New")
            self.assertEqual(p.read()["revision"],1)
            with self.assertRaises(ValueError):
                b.native.apply("invalid")
            result=b.native.apply(preview["proposal_token"])
            self.assertEqual(result["artifact"]["sha256"],preview["staged_sha256"])
            self.assertEqual(src.read_bytes(),original)
            with self.assertRaises(ValueError):
                b.native.apply(preview["proposal_token"])
            b.creation.recover("undo",result["revision"])
            self.assertEqual(p.read()["artifacts"]["world"]["sha256"],a["sha256"])
            with self.assertRaises(ValueError):
                b.native.preview(**args)

if __name__=="__main__":
    unittest.main()
