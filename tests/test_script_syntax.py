import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.script_syntax import definition, spans, export, language_for

def tokens(s,lang):
    return [(s[a:b],scope) for a,b,scope in spans(s,lang)]

class SyntaxTests(unittest.TestCase):
    def test_profiles(self):
        self.assertEqual(language_for("newvegas","test.txt"),"geck")
        self.assertEqual(language_for("morrowind","test.psc"),"papyrus")
        self.assertEqual(language_for("openmw","test.lua"),"lua")
        self.assertEqual(language_for("newvegas","test.obscript"),"oblivion")
    def test_papyrus_context(self):
        s='SCRIPTNAME Example\n;/ If\nEndIf /;\nString x = "If; test"\nIf True\nEndIf'
        t=tokens(s,"papyrus")
        self.assertIn(("SCRIPTNAME","keyword.control"),t)
        self.assertIn(("String","storage.type"),t)
        self.assertIn(("If; test","string.quoted.double"),t)
        self.assertIn(("EndIf ","comment.block"),t)
        self.assertIn(("True","constant.language"),t)
    def test_lua_case_and_long_comment(self):
        s="--[=[\nif false\n]=]\nif true then\nIF = 3\nend"
        t=tokens(s,"lua")
        self.assertIn(("if false","comment.block"),t)
        self.assertIn(("if","keyword.control"),t)
        self.assertNotIn(("IF","keyword.control"),t)
    def test_legacy(self):
        for lang in ("geck","oblivion","morrowind"):
            self.assertIn(("BEGIN","keyword.control"),tokens("BEGIN GameMode",lang))
            self.assertIn(("short","storage.type"),tokens("short count",lang))
    def test_unclosed_single_line_string(self):
        self.assertIn(("If","keyword.control"),tokens('"If\nIf True',"papyrus"))
    def test_spans_nonoverlapping(self):
        s='Scriptname X\r\nString t = "test"\r\n; comment\r\n'
        result=list(spans(s,"papyrus"))
        self.assertTrue(all(0<=a<b<=len(s) for a,b,_ in result))
        self.assertTrue(all(x[1]<=y[0] for x,y in zip(result,result[1:])))
    def test_export(self):
        with TemporaryDirectory() as d:
            for language in ("papyrus","geck","oblivion","morrowind","lua"):
                path=Path(d)/(language+".sublime-syntax")
                export(language,path)
                s=path.read_text()
                self.assertIn("contexts:",s)
                self.assertIn("version: 2",s)
                self.assertIn("scope: source."+language,s)
                self.assertIn("main",definition(language)["contexts"])
                with self.assertRaises(FileExistsError):
                    export(language,path)
