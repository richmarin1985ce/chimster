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

    def test_world_revision(self):
        from chimster.fnv_world import build
        from chimster.worldspace import Terrain
        from chimster.fnv_records import scan
        with TemporaryDirectory() as d:
            root=Path(d);a=root/"a";b=root/"b";a.mkdir();b.mkdir()
            t=Terrain(tuple(tuple(0. for _ in range(33)) for _ in range(33)))
            static=lambda id:{"id":id,"model":id+".nif","bounds":[0,0,0,1,1,1]}
            x={"statics":[static("Tree")],"placements":[{"id":"TreeOne","base":"Tree","x_m":1,"y_m":1,"z_m":0}]}
            first=FormIDs("World.esp");build(t,a/"World.esp",content=x,allocator=first)
            x["statics"].insert(0,static("Rock"))
            second=FormIDs("World.esp",first.snapshot());build(t,b/"World.esp",content=x,allocator=second)
            self.assertTrue(all(second.entries[k]==v for k,v in first.entries.items()))
            self.assertEqual(len(scan(b/"World.esp")["records"]),len(scan(a/"World.esp")["records"])+1)
    def test_quest_revision(self):
        from chimster.fnv_quest import export
        with TemporaryDirectory() as d:
            a=Path(d)/"a";b=Path(d)/"b";a.mkdir();b.mkdir()
            spec={"schema":1,"id":"Quest","title":"Quest","stages":[{"index":0,"log":"Start"}],"topics":[{"id":"Ask","prompt":"Ask","responses":[{"id":"Reply","text":"Hello"}]}]}
            first=FormIDs("Quest.esp");export(spec,a/"Quest.esp",allocator=first)
            spec["topics"][0]["responses"].insert(0,{"id":"New","text":"New"})
            second=FormIDs("Quest.esp",first.snapshot());export(spec,b/"Quest.esp",allocator=second)
            self.assertTrue(all(second.entries[k]==v for k,v in first.entries.items()))
