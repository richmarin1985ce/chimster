import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fnv_quest import export
from chimster.fnv_records import scan
class NativeQuestTests(unittest.TestCase):
    def test_records(self):
        s={"schema":1,"id":"TestQuest","title":"Test","stages":[{"index":0,"log":"Start"},{"index":10,"log":"End","complete":True}],"objectives":[{"index":10,"text":"Reach the gate"}],"topics":[{"id":"Ask","prompt":"Ask","responses":[{"text":"Hello","choices":["Leave"]}]},{"id":"Leave","prompt":"Leave","responses":[{"text":"Goodbye","goodbye":True}]}]}
        with TemporaryDirectory() as d:
            p=Path(d)/"Quest.esp";r=export(s,p)
            self.assertEqual(r["responses"],2)
            self.assertEqual([x["signature"] for x in scan(p)["records"]],["DIAL","INFO","DIAL","INFO","QUST"])
            s["topics"][0]["responses"][0]["choices"]=["Missing"]
            with self.assertRaises(ValueError):export(s,Path(d)/"Bad.esp")
