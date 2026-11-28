import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fnv_interior import export
from chimster.fnv_records import scan
from chimster.master_remap import reorder
from chimster.world_validator import validate
from chimster.record_graph import Slots
from chimster.native_world import world_records
from chimster.formids import FormIDs

class InteriorNativeTests(unittest.TestCase):
    def fixture(self):
        return {"schema":1,"statics":[{"id":"Rock","bounds":[-1,-1,-1,1,1,1],"model":"meshes/rock.nif"}],
                "cells":[{"id":"Room","title":"Room","placements":[
                    {"id":"Anchor","base":"Rock","position":[0,0,0],"persistent":True},
                    {"id":"Prop","base":"Rock","position":[1,2,3]}]}]}

    def test_remap_and_quest_target(self):
        from chimster.record_project import export as records
        from chimster.fnv_quest import export as quest
        with TemporaryDirectory() as d:
            root=Path(d);source=root/"Interior.esp";master=root/"A.esp"
            export(self.fixture(),source)
            records({"schema":1,"records":[{"id":"Global","type":"GLOB","fields":{"kind":"f","value":1.}}]},master)
            stage=root/"stage";stage.mkdir();dest=stage/source.name
            result=reorder(source,dest,[master],allow_set_change=True)
            self.assertEqual(result["changed_group_owners"],3)
            def inspect(path):
                slots=Slots(path.name,scan(path)["masters"])
                return [(r["key"],r["cell"],r["bucket"],r["persistent"],r["edges"])
                        for r in world_records("new-vegas",path.read_bytes(),slots)]
            self.assertEqual(inspect(source),inspect(dest))
            report=validate([master,dest])
            self.assertTrue(report["valid"],report["issues"])
            self.assertEqual(report["interior_cells"],1)
            self.assertEqual(report["persistent_references"],1)
            anchor=next(r for r in scan(dest)["records"] if r["signature"]=="REFR" and r["flags"]&0x400)
            target={"plugin":dest.name,"id":anchor["local_id"]}
            q=root/"Quest.esp"
            quest({"schema":1,"id":"Quest","title":"Quest","stages":[{"index":0,"log":"Start"}],
                   "objectives":[{"index":1,"text":"Find anchor","targets":[{"ref":target}]}]},q,[master,dest])
            report=validate([master,dest,q],quest_links=True)
            self.assertTrue(report["valid"],report["issues"])

    def test_stable_placement_identity(self):
        with TemporaryDirectory() as d:
            root=Path(d);a=root/"Interior.esp";ids=FormIDs(a.name)
            spec=self.fixture();export(spec,a,allocator=ids)
            folder=root/"revision";folder.mkdir();b=folder/a.name
            spec["cells"][0]["placements"].reverse()
            revised=FormIDs(b.name,ids.snapshot());export(spec,b,allocator=revised)
            self.assertEqual(ids.snapshot()["entries"],revised.snapshot()["entries"])
