import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from subprocess import CompletedProcess
from chimster.compiler_diagnostics import parse, navigation, summarize
from chimster.papyrus_build import compiler_options
from chimster.legacy_compile import lint, prepare, inspect, attach, encode
from chimster.lua_compile import check

def plugin(source,code,game):
    hs=8 if game=="morrowind" else 6
    def rec(sig,body,fid=0):
        h=struct.pack("<4sIII",sig,len(body),0,fid)
        return h+bytes({"morrowind":0,"oblivion":4,"fallout3":8,"newvegas":8}[game])+body
    if game=="morrowind":
        header=rec(b"TES3",b"")
        script=encode([(b"SCHD",b"Demo"+bytes(28)+struct.pack("<5I",0,0,0,len(code),0)),(b"SCDT",code),(b"SCTX",source)],hs)
    else:
        header=rec(b"TES4",b"")
        script=encode([(b"EDID",b"Demo\0"),(b"SCHR",struct.pack("<4xIIIHH",0,len(code),0,0,0)),(b"SCDA",code),(b"SCTX",source)],hs)
    return header+rec(b"SCPT",script,0x800 if game!="morrowind" else 0)

class CompilerTests(unittest.TestCase):
    def test_diagnostics(self):
        items=parse("C:\\src\\Demo.psc(4,2): warning test\nDemo.psc:8:9: error: bad\nline 9: bad",default_file="Demo.psc")
        self.assertEqual(summarize(items)["error"],2)
        self.assertEqual(navigation(items[0],r"C:\src\Demo.psc","\n"*4),"4.0")
        self.assertIsNone(navigation(items[0],r"C:\other\Demo.psc","\n"*4))
    def test_switches(self):
        self.assertEqual(compiler_options("skyrim","caprica",optimize=True,warnings_as_errors=True),["--optimize","--all-warnings-as-errors"])
        with self.assertRaises(ValueError):compiler_options("skyrim","ck",final=True)
    def test_legacy_lint(self):
        self.assertFalse(lint("Begin Demo\nif x\nendif\nEnd Demo","morrowind")["issues"])
        self.assertTrue(lint("scn Demo\nbegin GameMode\nif x\nend","newvegas")["issues"])
    def test_legacy_handoff(self):
        for game in ("morrowind","oblivion","fallout3","newvegas"):
            with self.subTest(game=game),TemporaryDirectory() as t:
                root=Path(t)
                for folder in ("old","draft","donor","final"):(root/folder).mkdir()
                p,d,c,q=[root/f/"Demo.esp" for f in ("old","draft","donor","final")]
                old="Begin Demo\nEnd Demo" if game=="morrowind" else "scn Demo\nBegin GameMode\nEnd"
                new=old+"\n; changed"
                p.write_bytes(plugin(old.encode(),b"old",game))
                src=root/"Demo.txt";src.write_text(new)
                prepare(p,d,game,"Demo" if game=="morrowind" else "0x800",src)
                self.assertEqual(inspect(d,game)["scripts"][0]["compiled_bytes"],0)
                c.write_bytes(plugin(new.replace("\n","\r\n").encode(),b"synthetic",game))
                attach(d,c,q,game)
                self.assertEqual(inspect(q,game)["scripts"][0]["compiled_bytes"],9)
                self.assertEqual(p.read_bytes(),plugin(old.encode(),b"old",game))
    def test_lua_check(self):
        with TemporaryDirectory() as t:
            root=Path(t);exe=root/"luac";exe.write_bytes(b"mock")
            src=root/"test.lua";src.write_text("return 1")
            with patch("chimster.lua_compile.subprocess.run",side_effect=[CompletedProcess([],0,"Lua 5.1.5",""),CompletedProcess([],0,"","")]):
                self.assertEqual(check(exe,src,execute=True)["status"],"syntax-checked")
            with patch("chimster.lua_compile.subprocess.run",return_value=CompletedProcess([],0,"Lua 5.4","")):
                self.assertEqual(check(exe,src,execute=True)["status"],"unsupported-version")
