import io
import json
import tempfile
import unittest
import wave
from pathlib import Path
from chimster.project import Project
from chimster.mcp_bridge import Bridge
from chimster.editor_presence import Presence
from chimster.editor_commands import mailbox,submit,consume,snapshot_result
from chimster.mcp_audio import normalize_pcm
from chimster.audio import wav_info

class FinalAdapterTests(unittest.TestCase):
    def test_audio(self):
        buf=io.BytesIO()
        with wave.open(buf,"wb") as f:
            f.setparams((2,2,8000,0,"NONE","not compressed"))
            f.writeframes(bytes(800*4))
        info=wav_info(normalize_pcm(buf.getvalue()))
        self.assertEqual((info["channels"],info["sample_width"],info["sample_rate"],info["frames"]),(1,2,16000,1600))

    def test_modeling(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=Project.create(root/"project","Demo","newvegas")
            q=root/"mesh.obj";q.write_text("v 0 0 0\nv 1 0 0\nv 0 0 1\nvt 0 0\nvt 1 0\nvt 0 1\nf 1/1 2/2 3/3\n")
            p.add("mesh","mesh",q,0)
            b=Bridge(p,allow_create=True);self.addCleanup(b.jobs.close)
            preview=b.production_preview("mesh-model",id="mesh",output_id="edited",revision=1,
                      edits_json=json.dumps([{"op":"split","index":0},{"op":"move","mode":"vertex","indices":[0],"delta":[0,.1,0]}]))
            self.assertEqual(preview["summary"]["edits"],2)
            b.production.apply(preview["proposal_token"])
            self.assertEqual(p.read()["revision"],2)
            self.assertEqual(p.object("mesh").read_bytes(),q.read_bytes())
            with self.assertRaises(ValueError):
                b.production_preview("mesh-model",id="mesh",output_id="bad",revision=2,edits_json='[{"op":"shell"}]')

    def test_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=Project.create(root/"project","Demo","newvegas")
            runtime=root/"runtime";presence=Presence(runtime)
            mailbox(presence.id,runtime,create=True);presence.publish(p)
            q=submit(p,presence.id,"viewport-state",0,root=runtime)
            key=q["request_id"]
            self.assertEqual(snapshot_result(p,presence.id,key,runtime)["state"],"pending_or_expired")
            consume(p,presence.id,lambda action,artifact:{"camera":{"yaw":10}},runtime)
            self.assertEqual(snapshot_result(p,presence.id,key,runtime)["snapshot"]["camera"]["yaw"],10)
            self.assertEqual(snapshot_result(p,presence.id,key,runtime)["state"],"pending_or_expired")
            q=submit(p,presence.id,"viewport-state",0,root=runtime)
            consume(p,presence.id,lambda action,artifact:None,runtime)
            self.assertEqual(snapshot_result(p,presence.id,q["request_id"],runtime)["state"],"denied")

if __name__=="__main__":
    unittest.main()
