import json
from pathlib import Path
import tempfile
import unittest
from chimster import lip_batch as lb,lip_pipeline as lp
from test_audio import wav
from test_lip_pipeline import lip

class LipBatchTests(unittest.TestCase):
    def test_stale(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=root/"src";old=root/"old";out=root/"out"
            key="Test.esp/Voice/Line";w=src/(key+".wav");w.parent.mkdir(parents=True);w.write_bytes(wav())
            p=old/key;p.mkdir(parents=True);(p/"voice.lip").write_bytes(lip())
            (p/"receipt.json").write_text(json.dumps({"game":"Skyrim","experimental":False,"source_sha256":lp.digest(wav()),"lip_sha256":lp.digest(lip()),"transcript_sha256":lp.digest(b"Hello")}))
            manifest={"game":"Skyrim","lines":[{"stem":key,"record":"Test.esp:123","text":"Hello"}]}
            self.assertEqual(lb.batch(src,old,out,manifest)["results"][0]["status"],"current")
            manifest["lines"][0]["text"]="Changed"
            self.assertEqual(lb.batch(src,old,out,manifest)["results"][0]["status"],"planned")
            self.assertFalse(out.exists())
            self.assertEqual(lb.batch(src,old,out,manifest,execute=True)["results"][0]["status"],"blocked")
