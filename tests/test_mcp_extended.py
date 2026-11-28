import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from chimster.project import Project
from chimster.worldspace import Terrain
from chimster.fnv_world import build
from chimster.mcp_extended import native_browse, native_profile
from chimster.mcp_bridge import Bridge,VERSIONS

class ExtendedTests(unittest.TestCase):
    def test_native_and_mesh(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=Project.create(root/"project","Demo","newvegas")
            src=root/"World.esp"
            build(Terrain(tuple(tuple(0. for _ in range(33)) for _ in range(33))),src,title="Demo")
            p.add("world","plugin",src,0)
            report=native_browse(p,"world",signature="WRLD",validate=True)
            self.assertEqual(report["total"],1)
            self.assertEqual(report["records"][0]["signature"],"WRLD")
            self.assertTrue(report["records"][0]["identity"])
            self.assertEqual(native_profile("skyrimse"),"skyrim-se")
            self.assertEqual(native_profile("openmw"),"morrowind")
            with self.assertRaises(ValueError):native_profile("starfield")
            obj=root/"triangle.obj"
            obj.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n")
            p.add("mesh","mesh",obj,1)
            a=p.read()["artifacts"]["mesh"]
            args=dict(id="mesh",output_id="scaled",scale_percent=200,yaw_degrees=0,
                      ground=False,revision=2,sha256=a["sha256"])
            b=Bridge(p,allow_create=True,allow_edit=True)
            self.addCleanup(b.jobs.close)
            q=b.mesh.preview(**args)
            self.assertEqual(p.read()["revision"],2)
            result=b.mesh.apply(q["proposal_token"])
            self.assertEqual(result["artifact"]["sha256"],q["sha256"])
            self.assertEqual(p.read()["artifacts"]["mesh"],a)
            with self.assertRaises(ValueError):b.mesh.apply(q["proposal_token"])
            b.creation.recover("undo",result["revision"])
            self.assertNotIn("scaled",p.read()["artifacts"])
    def test_stdio_client_versions(self):
        for version in VERSIONS:
            with self.subTest(version=version):
                requests=[{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":version,"capabilities":{},"clientInfo":{"name":"external-process-test","version":"1"}}},
                          {"jsonrpc":"2.0","method":"notifications/initialized"},
                          {"jsonrpc":"2.0","id":2,"method":"tools/list"},
                          {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"chimster_capabilities"}}]
                result=subprocess.run([sys.executable,"-m","chimster","--mcp"],input="".join(json.dumps(r)+"\n" for r in requests),
                                      text=True,capture_output=True,timeout=30,check=True)
                rows=[json.loads(line) for line in result.stdout.splitlines()]
                self.assertEqual([r["id"] for r in rows],[1,2,3])
                self.assertEqual(rows[0]["result"]["protocolVersion"],version)
                self.assertEqual(rows[1]["result"]["tools"][0]["name"],"chimster_capabilities")
                self.assertEqual(json.loads(rows[2]["result"]["content"][0]["text"])["access"],"read-only")

if __name__=="__main__":
    unittest.main()
