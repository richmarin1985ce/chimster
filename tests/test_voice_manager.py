import json
from pathlib import Path
import tempfile
import unittest
from chimster import audio, voice_manager as vm
from test_audio import xwm

class VoiceManagerTests(unittest.TestCase):
    def test_paths(self):
        for s in ("../Voice/Line", "X.esp/../Line", "X.esp/V/CON", "X.esp/V/line.fuz", "X.esp/V/a\\b"):
            with self.assertRaises(ValueError): vm.stem(s)

    def test_batch(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/"src"; dest=Path(t)/"out"
            line=root/"Test.esp"/"Voice"/"Line"
            line.parent.mkdir(parents=True)
            line.with_suffix(".xwm").write_bytes(xwm())
            line.with_suffix(".lip").write_bytes(b"synthetic")
            m={"game":"Skyrim","lines":[{"stem":"Test.esp/Voice/Line","record":"Test.esp:123","text":"Hello"},{"stem":"Test.esp/Voice/Missing","record":"Test.esp:124","text":"Bye"}]}
            p=Path(t)/"manifest.json"; p.write_text(json.dumps(m))
            m=vm.load_manifest(p)
            self.assertEqual([r["status"] for r in vm.audit(root,m)["lines"]],["source-ready","missing"])
            report=vm.batch_pack(root,dest,m)
            self.assertEqual([r["status"] for r in report["results"]],["planned","blocked"])
            self.assertFalse(dest.exists())
            report=vm.batch_pack(root,dest,m,execute=True)
            self.assertEqual(report["results"][0]["status"],"written")
            self.assertEqual(audio.unpack_fuz((dest/"Test.esp/Voice/Line.fuz").read_bytes()),(b"synthetic",xwm()))
            self.assertEqual(vm.batch_pack(root,dest,m,execute=True)["results"][0]["status"],"blocked")
            with self.assertRaises(ValueError):vm.batch_pack(root,root/"output",m)

    def test_duplicate(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"m.json"
            line={"stem":"Test.esp/V/Line","record":"Test.esp:1","text":"test"}
            p.write_text(json.dumps({"game":"Skyrim","lines":[line,{**line,"stem":"test.esp/v/LINE"}]}))
            with self.assertRaises(ValueError):vm.load_manifest(p)
