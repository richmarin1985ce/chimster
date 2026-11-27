import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.dialogue_views import generate_graph

class GraphAdapterTests(unittest.TestCase):
    def test_explicit_bindings(self):
        graph={"nodes":[{"id":"a","caption":"Start"},{"id":"b","caption":"End"}],"edges":[{"source":"a","target":"b"}]}
        with TemporaryDirectory() as d:
            p=Path(d)/"02000800.xml"
            with self.assertRaises(ValueError):generate_graph(p,graph,{"a":"02000801"})
            self.assertFalse(p.exists())
            report=generate_graph(p,graph,{"a":"02000801","b":"02000802"})
            self.assertEqual(report["record_form_ids"],["02000801","02000802"])
            self.assertEqual(len(report["links"]),1)
