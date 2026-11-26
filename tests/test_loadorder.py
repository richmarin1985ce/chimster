import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.loadorder import dependency_order,HeaderCache,scan_profile
from chimster.autopatch import plan

class LoadOrderTests(unittest.TestCase):
    def test_sort(self):
        self.assertEqual(dependency_order([{"name":"B.esp","masters":["A.esm"]},{"name":"A.esm","masters":[]}]),["A.esm","B.esp"])
    def test_missing(self):
        with self.assertRaises(ValueError): dependency_order([{"name":"B.esp","masters":["A.esm"]}])
    def test_cycle(self):
        with self.assertRaises(ValueError): dependency_order([{"name":"A.esp","masters":["B.esp"]},{"name":"B.esp","masters":["A.esp"]}])
    def test_cache(self):
        with TemporaryDirectory() as d:
            root=Path(d);p=root/"A.esm";p.write_bytes(b"TES4"+bytes(20))
            c=HeaderCache(root/"cache.sqlite")
            try:
                self.assertEqual(scan_profile("newvegas",[root],["A.esm"],c)["cache_hits"],0)
                self.assertEqual(scan_profile("newvegas",[root],["A.esm"],c)["cache_hits"],1)
                p.write_bytes(b"TES4"+bytes(20)+b"STAT"+bytes(20))
                self.assertEqual(scan_profile("newvegas",[root],["A.esm"],c)["cache_hits"],0)
            finally:c.close()

class PatchTests(unittest.TestCase):
    def inputs(self):
        plugins=[{"name":"Base.esm","masters":[]},{"name":"Patch.esp","masters":["Base.esm"],"patch_candidate":True,"side_effects_clear":True,"merge_reviewed":True}]
        records=[{"origin":"Base.esm","local_id":"800","provider":p,"signature":"STAT","safe_override":True,"semantic_sha256":h*64} for p,h in [("Base.esm","a"),("Patch.esp","b")]]
        return plugins,records
    def test_forward(self):
        p,r=self.inputs();x=plan(p,r,backend_version="fixture",complete_snapshot=True)
        self.assertEqual(x["review_candidates"],["Patch.esp"])
        self.assertEqual(len(x["forward_winning_overrides"]),1);self.assertFalse(x["disables_plugins"])
    def test_duplicate(self):
        p,r=self.inputs();r[1]["semantic_sha256"]="a"*64
        self.assertEqual(len(plan(p,r,backend_version="fixture",complete_snapshot=True)["redundant_overrides"]),1)
    def test_incomplete(self):
        p,r=self.inputs();self.assertFalse(plan(p,r,backend_version="fixture")["review_candidates"])
    def test_dependent(self):
        p,r=self.inputs();p.append({"name":"Other.esp","masters":["Patch.esp"]})
        self.assertFalse(plan(p,r,backend_version="fixture",complete_snapshot=True)["review_candidates"])
    def test_new_form(self):
        p,r=self.inputs();r[1]["origin"]="Patch.esp"
        self.assertFalse(plan(p,r,backend_version="fixture",complete_snapshot=True)["review_candidates"])
