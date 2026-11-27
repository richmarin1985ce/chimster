import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.dialogue_views import generate,parse,inspect,remap

class GenerateTests(unittest.TestCase):
    def test_generate_roundtrip(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"02000800.xml"
            nodes=[{"id":"a","form_id":"02000801","caption":"A & B"},{"id":"b","form_id":"02000802","caption":"Second"}]
            result=generate(p,nodes,[("a","b"),("b","a")])
            self.assertEqual(result["nodes"][0]["caption"],"A & B")
            self.assertEqual(len(result["links"]),2)
            q=Path(d)/"03000800.xml"
            remap(p,q,{"02000800":"03000800","02000801":"03000801","02000802":"03000802"})
            self.assertEqual(inspect(parse(q))["record_form_ids"],["03000801","03000802"])
    def test_invalid_graph_no_output(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"02000800.xml"
            nodes=[{"id":"a","form_id":"02000801","caption":"A"}]
            with self.assertRaises(ValueError):generate(p,nodes,[("a","missing")])
            self.assertFalse(p.exists())
            with self.assertRaises(ValueError):generate(p,nodes+nodes,[])
            self.assertFalse(p.exists())
