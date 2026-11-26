import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.worldspace import Terrain
from chimster.fnv_world import build
from chimster.record_editor import inspect,edit_text
class EditorTests(unittest.TestCase):
    def test_edit(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"World.esp";q=Path(d)/"stage";q.mkdir()
            t=Terrain(tuple(tuple(0. for _ in range(33)) for _ in range(33)))
            build(t,p,title="Old");original=p.read_bytes()
            r=inspect(p,p.name,0x800)
            a=edit_text(p,q/p.name,p.name,0x800,"FULL","Longer new title",r["payload_sha256"])
            self.assertNotEqual(a["old_hash"],a["new_hash"])
            self.assertEqual(p.read_bytes(),original)
            self.assertEqual(a["untouched_records"],3)
            with self.assertRaises(ValueError):edit_text(p,q/"Different.esp",p.name,0x800,"FULL","X",r["payload_sha256"])
