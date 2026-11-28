import struct
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from chimster.papyrus_build import build, diagnostics, inspect_pex, plan

def fixture(endian=">", target=1):
    return struct.pack(endian + "IBBHQ", 0xFA57C0DE, 3, 2, target, 0) + b"\0\0"*4

class PapyrusBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        src = self.root / "source"
        src.mkdir()
        self.source = src / "Example.psc"
        self.source.write_text("Scriptname Example extends Quest\n")
        self.flags = src / "Game.flg"
        self.flags.write_text("fixture")
        self.exe = self.root / "compiler.exe"
        self.exe.write_bytes(b"mock tool")
        self.out = self.root / "build"
    def args(self):
        return ("skyrimse", "ck", self.exe, self.source, self.flags, [], self.out)
    def test_preview(self):
        p = plan(*self.args())
        self.assertIn("-o="+str(self.out), p["args"])
        self.assertFalse(self.out.exists())
        self.assertEqual(p["lint"]["script_names"], ["example"])
    def test_wrong_target_and_truncation(self):
        p = self.root / "test.pex"
        p.write_bytes(fixture())
        self.assertEqual(inspect_pex(p, "skyrimvr")["game_id"], 1)
        with self.assertRaises(ValueError):
            inspect_pex(p, "fallout4")
        p.write_bytes(fixture("<", 2))
        self.assertEqual(inspect_pex(p, "fallout4vr")["game_id"], 2)
        p.write_bytes(b"short")
        with self.assertRaises(ValueError):
            inspect_pex(p, "skyrim")
    def test_success_staged(self):
        def run(args, **kwargs):
            self.assertFalse(kwargs["shell"])
            dest = Path(next(a[3:] for a in args if a.startswith("-o=")))
            (dest / "Example.pex").write_bytes(fixture())
            return subprocess.CompletedProcess(args, 0, "compiled", "")
        with patch("chimster.papyrus_build.subprocess.run", side_effect=run):
            result = build(*self.args(), execute=True)
        self.assertEqual(result["status"], "header-checked")
        self.assertTrue((self.out / "Example.pex").exists())
        self.assertTrue((self.out / "compile.json").exists())
        with self.assertRaises(FileExistsError):
            plan(*self.args())
    def test_failure_does_not_publish(self):
        with patch("chimster.papyrus_build.subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "Example.psc(3,2): bad syntax")):
            result = build(*self.args(), execute=True)
        self.assertEqual(result["status"], "compiler-failed")
        self.assertEqual(result["diagnostics"][0]["line"], 3)
        self.assertFalse(self.out.exists())
    def test_timeout(self):
        with patch("chimster.papyrus_build.subprocess.run", side_effect=subprocess.TimeoutExpired([], 1)):
            self.assertEqual(build(*self.args(), execute=True)["status"], "timeout")
        self.assertFalse(self.out.exists())
    def test_diagnostics(self):
        d = diagnostics("C:\\src\\Example.psc(4,5): warning something\nExample.psc:7:9: error\nother")
        self.assertEqual([x["severity"] for x in d], ["warning", "error", "info"])
        self.assertEqual(d[1]["column"], 9)
    def test_in_source_rejected(self):
        with self.assertRaises(ValueError):
            plan(*self.args()[:-1], self.source.parent / "build")
    def test_legacy_rejected(self):
        with self.assertRaises(ValueError):
            plan("newvegas", *self.args()[1:])
    def test_wrong_output_no_publish(self):
        with patch("chimster.papyrus_build.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "", "")):
            self.assertEqual(build(*self.args(), execute=True)["status"], "unexpected-output")
        self.assertFalse(self.out.exists())
