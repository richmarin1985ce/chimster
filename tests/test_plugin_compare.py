import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.fnv_world import build
from chimster.worldspace import Terrain
from chimster.plugin_compare import compare
class CompareTests(unittest.TestCase):
    def test_compare(self):
        with TemporaryDirectory() as d:
            a=Path(d)/"a";b=Path(d)/"b";a.mkdir();b.mkdir()
            t=Terrain(tuple(tuple(0. for _ in range(33)) for _ in range(33)))
            build(t,a/"World.esp",title="A");build(t,b/"World.esp",title="B")
            r=compare(a/"World.esp",b/"World.esp")
            self.assertEqual(len(r["changed"]),1);self.assertEqual(r["added"],[]);self.assertEqual(r["removed"],[])
