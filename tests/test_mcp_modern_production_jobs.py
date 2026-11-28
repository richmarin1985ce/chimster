import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from chimster.project import Project
from chimster.mcp_bridge import Bridge
from chimster.mcp_modern import VERSION,PREFIX
from chimster.mcp_production_jobs import ProductionJobs

class ModernProductionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.p=Project.create(self.root/"project","Demo","newvegas")
        self.b=Bridge(self.p)
        self.addCleanup(self.b.jobs.close)
        self.addCleanup(self.b.production_jobs.close)
    def request(self,method,**params):
        return self.b.dispatch({"jsonrpc":"2.0","id":1,"method":method,
            "params":{**params,"_meta":{PREFIX+"protocolVersion":VERSION,PREFIX+"clientCapabilities":{}}}})
    def test_modern(self):
        discover=self.request("server/discover")["result"]
        self.assertEqual(discover["supportedVersions"],[VERSION])
        self.assertEqual(discover["resultType"],"complete")
        names={t["name"] for t in self.request("tools/list")["result"]["tools"]}
        self.assertIn("project_status",names)
        self.assertNotIn("production_start",names)
        self.assertNotIn("editor_context",names)
        self.assertEqual(json.loads(self.request("tools/call",name="project_status")["result"]["content"][0]["text"])["name"],"Demo")
        self.assertIn("error",self.request("tools/call",name="project_apply_create"))
        self.assertIn("error",self.request("resources/read",uri="chimster://editor/context"))
    def test_isolated_production(self):
        import wave
        src=self.root/"voice.wav"
        with wave.open(str(src),"wb") as f:
            f.setparams((1,2,8000,0,"NONE","not compressed"))
            f.writeframes(bytes(1600))
        self.p.add("voice","audio",src,0)
        b=Bridge(self.p,allow_create=True,allow_edit=True)
        self.addCleanup(b.jobs.close);self.addCleanup(b.production_jobs.close)
        result=b.production_start("audio-normalize",id="voice",output_id="converted",revision=1)
        key=result["job_id"]
        b.production_jobs.entry[3].result(timeout=45)
        preview=b.production_jobs.collect(key)
        self.assertEqual(self.p.read()["revision"],1)
        after=b.production.apply(preview["proposal_token"])
        self.assertEqual(after["revision"],2)
        self.assertEqual(after["outputs"][0]["sha256"],preview["outputs"][0]["sha256"])
    def test_cancel(self):
        # A mock worker that remains running until killed.
        from subprocess import TimeoutExpired
        import threading
        started=threading.Event()
        class Process:
            killed=False
            returncode=None
            def communicate(self,input=None,timeout=None):
                if self.killed:return b"",None
                started.set()
                time.sleep(.03)
                raise TimeoutExpired("worker",timeout)
            def poll(self):return -9 if self.killed else None
            def kill(self):self.killed=True
        proc=Process()
        with patch("chimster.mcp_production_jobs.subprocess.Popen",return_value=proc):
            job=self.b.production_start("audio-normalize",id="voice",output_id="converted",revision=0)["job_id"]
            self.assertTrue(started.wait(5))
            self.b.production_jobs.cancel(job)
            with self.assertRaises(ValueError):self.b.production_jobs.entry[3].result(timeout=5)
            self.assertTrue(proc.killed)
            self.assertEqual(self.b.production_jobs.status(job)["state"],"cancelled")
            self.assertIsNone(self.b.production.pending)

if __name__=="__main__":
    unittest.main()
