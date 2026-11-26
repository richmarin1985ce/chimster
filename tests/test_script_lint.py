import unittest
from chimster.script_lint import check
class ScriptTests(unittest.TestCase):
    def test_balanced(self):
        self.assertTrue(check('Scriptname Test\nEvent OnInit()\nIf true\nDebug.Trace("EndIf") ; endevent\nEndIf\nEndEvent\n')["valid"])
    def test_bad(self):
        r=check("Scriptname Test\nEvent OnInit()\nWhile true\nEndEvent\n")
        self.assertFalse(r["valid"]);self.assertTrue(any("Unclosed" in i["message"] for i in r["issues"]))
