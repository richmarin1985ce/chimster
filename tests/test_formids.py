import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.formids import FormIDs,staged_build
class FormIDTests(unittest.TestCase):
    def test_stable(self):
        a=FormIDs("Test.esp");x=a.get("STAT/Tree");y=a.get("REFR/Tree1")
        b=FormIDs("Test.esp",a.snapshot());self.assertEqual(b.get("REFR/Tree1"),y)
        z=b.get("STAT/Rock");self.assertGreater(z,y)
        c=FormIDs("Test.esp",b.snapshot());self.assertEqual(c.get("STAT/Tree"),x)
        with self.assertRaises(ValueError):c.get("STAT/Tree")
        with self.assertRaises(ValueError):FormIDs("Other.esp",a.snapshot())
    def test_staged(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Test.esp";q=Path(d)/"ids.json"
            def build(ids):
                ids.get("STAT/A");p.write_bytes(b"fixture");return {"ok":True}
            self.assertEqual(staged_build(build,p,q)["allocated_ids"],1)
            self.assertTrue(q.is_file())
