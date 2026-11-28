import unittest
from chimster.archive_precedence import plan
from chimster.archive_config import parse
from chimster.compatibility_asset_lookup import index,resolve

class PrecedenceTests(unittest.TestCase):
    def test_registration(self):
        self.assertEqual(parse("morrowind","[Archives]\nArchive 2=B.bsa\nArchive 0=A.bsa")["base_archives"],["A.bsa","B.bsa"])
    def test_order(self):
        result=plan("fallout4",["A.esp","B.esp"],["B - Main.ba2","A - Main.ba2","Base.ba2","Other.ba2"],base_archives=["Base.ba2"],loose=["Data"],loose_policy="last")
        self.assertEqual(result["layers"],["Base.ba2","A - Main.ba2","B - Main.ba2","Data"])
        self.assertEqual(result["unassociated"],["Other.ba2"])
    def test_explicit_policy(self):
        with self.assertRaises(ValueError):plan("fallout4",[],[])
    def test_conflict(self):
        catalog=index([("base",[("textures/a.dds",1)]),("mod",[("Textures/A.dds",2)])])
        self.assertEqual(resolve(catalog,"textures/a.dds")["winner"]["locator"],2)
