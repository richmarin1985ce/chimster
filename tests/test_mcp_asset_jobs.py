import tempfile
import threading
import unittest
import wave
from pathlib import Path
from chimster.project import Project
from chimster.mcp_operations import inspect_asset
from chimster.mcp_jobs import Jobs
from chimster.mcp_bridge import Bridge

class AssetJobTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.p=Project.create(self.root/"project","Example","newvegas")
        path=self.root/"voice.wav"
        with wave.open(str(path),"wb") as f:
            f.setparams((1,2,8000,0,"NONE","not compressed"))
            f.writeframes(bytes(1600))
        self.p.add("voice","audio",path,0)
    def test_audio(self):
        report=inspect_asset(self.p,"voice","audio")
        self.assertEqual(report["result"]["sample_rate"],8000)
        self.assertAlmostEqual(report["result"]["duration"],.1)
        with self.assertRaises(ValueError):
            inspect_asset(self.p,"voice","font")
    def test_job_lifecycle(self):
        b=Bridge(self.p)
        self.addCleanup(b.jobs.close)
        start=b.start_job("audio","voice")
        key=start["job_id"]
        b.jobs.entries[key][2].result(timeout=5)
        self.assertEqual(b.jobs.result(key)["state"],"completed")
        self.assertEqual(b.jobs.result(key)["result"]["id"],"voice")
        b.jobs.discard(key)
        self.assertNotIn(key,b.jobs.entries)
        with self.assertRaises(ValueError):
            b.start_job("shell","voice")
    def test_queued_cancel_and_revision_guard(self):
        jobs=Jobs(self.p)
        self.addCleanup(jobs.close)
        entered=threading.Event()
        release=threading.Event()
        def work():
            entered.set()
            if not release.wait(5):raise ValueError("timeout")
            return {"ok":True}
        first=jobs.start("check",work)["job_id"]
        try:
            self.assertTrue(entered.wait(5))
            second=jobs.start("check",lambda:{"ok":True})["job_id"]
            self.assertTrue(jobs.cancel(second)["cancelled_now"])
            self.assertEqual(jobs.status(second)["state"],"cancelled")
            p=self.root/"text.txt"
            p.write_text("changed")
            self.p.add("new","other",p,1)
        finally:
            release.set()
        with self.assertRaises(ValueError):
            jobs.entries[first][2].result(timeout=5)
        self.assertEqual(jobs.status(first)["state"],"failed")

if __name__=="__main__":
    unittest.main()
