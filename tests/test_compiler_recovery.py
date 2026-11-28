import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from subprocess import CompletedProcess
from chimster.pex_decompile import decompile
from chimster.papyrus_batch import batch
from chimster.compiler_diagnostics import remap

def fixture():
    return struct.pack(">IBBHQ",0xFA57C0DE,3,2,1,0)+b"\0\0"*4

class CompilerRecoveryTests(unittest.TestCase):
    def test_decompile(self):
        with TemporaryDirectory() as t:
            root=Path(t);exe=root/"champollion";exe.write_bytes(b"mock")
            src=root/"Demo.pex";src.write_bytes(fixture())
            out=root/"recovered"
            def run(args,**kwargs):
                Path(args[-1],"Demo.psc").write_text("Scriptname Demo\n")
                return CompletedProcess(args,0,"","")
            with patch("chimster.pex_decompile.subprocess.run",side_effect=run):
                self.assertEqual(decompile("skyrim",exe,src,out,execute=True)["status"],"source-recovered")
            self.assertTrue((out/"decompile.json").is_file())
            self.assertEqual(src.read_bytes(),fixture())
    def test_recovery_failure(self):
        with TemporaryDirectory() as t:
            root=Path(t);exe=root/"champollion";exe.write_bytes(b"mock")
            src=root/"Demo.pex";src.write_bytes(fixture())
            out=root/"recovered"
            with patch("chimster.pex_decompile.subprocess.run",return_value=CompletedProcess([],0,"","")):
                self.assertEqual(decompile("skyrim",exe,src,out,execute=True)["status"],"unexpected-output")
            self.assertFalse(out.exists())
    def test_reuse_and_invalidation(self):
        with TemporaryDirectory() as t:
            root=Path(t);src=root/"src";src.mkdir();tools=root/"tools";tools.mkdir()
            exe=tools/"compiler";exe.write_bytes(b"fixture")
            flags=tools/"flags.flg";flags.write_text("flags")
            p=src/"Demo.psc";p.write_text("Scriptname Demo")
            def compile_mock(game,backend,exe,source,flags,imports,output,**kwargs):
                from hashlib import sha256
                output.mkdir();data=fixture();(output/"Demo.pex").write_bytes(data)
                return {"status":"header-checked","artifact":{"sha256":sha256(data).hexdigest()}}
            args=("skyrim","ck",exe,src,flags,[])
            first=root/"first";second=root/"second";third=root/"third"
            with patch("chimster.papyrus_batch.build",side_effect=compile_mock) as compiler:
                self.assertEqual(batch(*args,first,execute=True)["reused_count"],0)
                self.assertEqual(batch(*args,second,execute=True,reuse=first)["reused_count"],1)
                self.assertEqual(compiler.call_count,1)
                p.write_text("Scriptname Demo\n;changed")
                self.assertEqual(batch(*args,third,execute=True,reuse=second)["reused_count"],0)
                self.assertEqual(compiler.call_count,2)
    def test_source_map(self):
        source={"path":"/real/Demo.psc","sha256":"fixture"}
        mapping={"/tmp/source-0/Demo.psc":source}
        result=remap([{"file":"/tmp/source-0/Demo.psc","line":2},{"file":"/untrusted/Demo.psc","line":3}],mapping)
        self.assertEqual(result[0]["file"],source["path"])
        self.assertEqual(result[0]["source_sha256"],"fixture")
        self.assertEqual(result[1]["file"],"/untrusted/Demo.psc")
