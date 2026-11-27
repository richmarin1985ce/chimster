import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.dialogue_views import generate_graph

class BranchLayoutTests(unittest.TestCase):
    def test_container_bounds(self):
        graph={"nodes":[{"id":"a","caption":"Topic","branch":"b","bounds":[100,100,200,80]},{"id":"b","caption":"Branch","kind":"branch"}],"edges":[]}
        with TemporaryDirectory() as d:
            p=Path(d)/"02000800.xml"
            result=generate_graph(p,graph,{"a":"02000801","b":"02000802"})
            self.assertEqual(result["nodes"][0]["bounds"],[76,60,248,144])
            self.assertEqual(result["links"],[])
    def test_invalid_membership(self):
        graph={"nodes":[{"id":"a","caption":"Topic","branch":"missing"}],"edges":[]}
        with TemporaryDirectory() as d:
            p=Path(d)/"02000800.xml"
            with self.assertRaises(ValueError):generate_graph(p,graph,{"a":"02000801"})
            self.assertFalse(p.exists())
