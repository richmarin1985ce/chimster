import unittest
from chimster.script_symbols import catalog, local_symbols, complete, lookup

class ScriptSymbolTests(unittest.TestCase):
    def test_extenders_opt_in(self):
        self.assertFalse(lookup("newvegas","geck","","GetNVSEVersion"))
        self.assertEqual(lookup("newvegas","geck","","GetNVSEVersion",["xnvse"])[0].origin,"xnvse")
        self.assertFalse(lookup("fallout3","geck","","GetNVSEVersion",["xnvse"]))
        self.assertFalse(lookup("fallout4","papyrus","","GetVersion",["skse"]))
    def test_profile_family(self):
        self.assertTrue(lookup("skyrimvr","papyrus","","GetPlayer"))
        self.assertFalse(lookup("skyrim","papyrus","","GetValue"))
        self.assertTrue(lookup("fallout4","papyrus","","GetValue"))
        self.assertFalse(catalog("morrowind","papyrus"))
    def test_source_declarations(self):
        s='Scriptname Test\n; Function Bogus()\nInt Property Count Auto\nInt Function Calc()\nreturn 1\nEndFunction'
        items=local_symbols(s,"papyrus")
        self.assertEqual([x.name for x in items],["Test","Count","Calc"])
        self.assertEqual(lookup("skyrim","papyrus",s,"calc")[0].line,4)
    def test_multiline_comments(self):
        s='Scriptname Test\n;/\nFunction Fake()\n/;\nEvent Real()\nEndEvent'
        self.assertEqual([x.name for x in local_symbols(s,"papyrus")],["Test","Real"])
    def test_owner_filter(self):
        self.assertEqual(complete("skyrim","papyrus","","Get",owner="Quest")[0].name,"GetStage")
        self.assertEqual(complete("skyrim","papyrus","","GetP",owner="Game")[0].name,"GetPlayer")
    def test_lua_case(self):
        self.assertTrue(lookup("openmw","lua","","print"))
        self.assertFalse(lookup("openmw","lua","","PRINT"))
    def test_limit(self):
        self.assertEqual(len(complete("skyrim","papyrus","","",limit=2)),2)
        with self.assertRaises(ValueError):complete("skyrim","papyrus","","",limit=0)

    def test_local_library(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from chimster.script_symbols import index_papyrus_library
        with TemporaryDirectory() as d:
            root=Path(d)
            (root/"Custom.psc").write_text("Scriptname Custom\nInt Function Example()\nEndFunction")
            (root/"Ignore.txt").write_text("not a script")
            result=index_papyrus_library(root)
            self.assertEqual(result["files"],1)
            symbols=lookup("skyrim","papyrus","","Example",library=result["symbols"])
            self.assertEqual(symbols[0].origin,"library")
            self.assertEqual(symbols[0].owner,"Custom")
            self.assertTrue(symbols[0].path.endswith("Custom.psc"))
            (root/"Second.psc").write_text("Scriptname Second")
            with self.assertRaises(ValueError):index_papyrus_library(root,max_files=1)
