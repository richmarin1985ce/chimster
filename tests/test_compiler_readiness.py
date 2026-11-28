import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from subprocess import CompletedProcess
from chimster.compiler_profiles import discover,create,load,configured_build
from chimster.papyrus_build import build,import_fingerprints
from chimster.papyrus_runtime import analyze

class CompilerReadinessTests(unittest.TestCase):
    def test_discovery_and_pinning(self):
        with TemporaryDirectory() as t:
            root=Path(t);tools=root/"Papyrus Compiler";tools.mkdir()
            exe=tools/"PapyrusCompiler.exe";exe.write_bytes(b"fixture")
            src=root/"Data"/"Scripts"/"Source";src.mkdir(parents=True)
            flag=src/"TESV_Papyrus_Flags.flg";flag.write_text("fixture")
            with patch("chimster.compiler_profiles.shutil.which",return_value=None):
                info=discover("skyrimse",root)
            self.assertEqual(info["compilers"][0]["path"],str(exe.resolve()))
            self.assertIn(str(flag.resolve()),info["flags"])
            p=root/"profile.json"
            create(p,"skyrimse","ck",exe,flag,[src],options={"optimize":True})
            self.assertEqual(load(p)["switches"],["-optimize"])
            flag.write_text("changed")
            with self.assertRaises(ValueError):load(p)
    def test_profile_build_preview(self):
        with TemporaryDirectory() as t:
            root=Path(t);src=root/"src";src.mkdir();tools=root/"tools";tools.mkdir()
            exe=tools/"compiler";exe.write_bytes(b"fixture")
            flags=tools/"flags.flg";flags.write_text("fixture")
            p=src/"Demo.psc";p.write_text("Scriptname Demo")
            cfg=root/"profile.json";create(cfg,"skyrim","ck",exe,flags,[])
            report=configured_build(cfg,p,root/"out")
            self.assertEqual(report["game"],"skyrim")
            self.assertFalse((root/"out").exists())
    def test_nested_import_fingerprint(self):
        with TemporaryDirectory() as t:
            root=Path(t);nested=root/"nested";nested.mkdir()
            p=nested/"Demo.psc";p.write_text("a")
            old=import_fingerprints([root])
            p.write_text("b")
            self.assertNotEqual(old,import_fingerprints([root]))
    def test_zero_exit_with_error(self):
        with TemporaryDirectory() as t:
            root=Path(t);src=root/"src";src.mkdir();tools=root/"tools";tools.mkdir()
            exe=tools/"compiler";exe.write_bytes(b"fixture")
            flags=tools/"flags.flg";flags.write_text("fixture")
            p=src/"Demo.psc";p.write_text("Scriptname Demo")
            with patch("chimster.papyrus_build.subprocess.run",return_value=CompletedProcess([],0,"Demo.psc(2,1): error: invalid","")):
                self.assertEqual(build("skyrim","ck",exe,p,flags,[],root/"out",execute=True)["status"],"compiler-failed")
            self.assertFalse((root/"out").exists())
    def test_runtime_log(self):
        log='[11/28/2026 - 01:00AM] Error: Cannot call function\nstack:\n[Demo].Run() - "Demo.psc" Line 12\n[11/28/2026 - 01:01AM] Error: Cannot call function\n'
        report=analyze(log)
        self.assertEqual(report["counts"]["error"],2)
        self.assertEqual(report["repeated"][0]["count"],2)
        self.assertEqual(report["events"][0]["frames"][0]["line"],12)
