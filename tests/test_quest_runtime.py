import unittest,struct
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.fnv_patch import sub,record
from chimster.fnv_world import group,build
from chimster.worldspace import Terrain
from chimster.fnv_quest import export
from chimster.fnv_records import scan
from chimster.quest_scripts import plan
class RuntimeTests(unittest.TestCase):
    def test_bound_actor_faction_target(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Actors.esm";h=bytearray(record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,4,0x802))));struct.pack_into("<I",h,8,1)
            p.write_bytes(h+group(0,b"FACT",record(b"FACT",sub(b"EDID",b"Faction\0"),0x800))+group(0,b"NPC_",record(b"NPC_",sub(b"EDID",b"Actor\0"),0x801)))
            w=Path(d)/"World.esp"
            t=Terrain(tuple(tuple(0. for _ in range(33)) for _ in range(33)))
            build(t,w,content={"statics":[{"id":"Marker","model":"marker.nif","bounds":[0,0,0,1,1,1]}],"placements":[{"base":"Marker","x_m":1,"y_m":1,"z_m":0}]})
            ref=next(r["local_id"] for r in scan(w)["records"] if r["signature"]=="REFR")
            actor={"plugin":p.name,"id":0x801};faction={"plugin":p.name,"id":0x800}
            s={"schema":1,"id":"Quest","title":"Quest","stages":[{"index":10,"log":"Start"}],"objectives":[{"index":10,"text":"Go","targets":[{"ref":{"plugin":w.name,"id":ref}}]}],"topics":[{"id":"Ask","prompt":"Ask","responses":[{"text":"Hello","speaker":actor,"conditions":[{"actor":actor,"is":True},{"faction":faction,"member":True}]}]}]}
            out=Path(d)/"Quest.esp";r=export(s,out,[p,w]);self.assertEqual(r["quest"],0x02000800);self.assertEqual(scan(out)["masters"],[p.name,w.name])
            with self.assertRaises(ValueError):export(s,Path(d)/"Bad.esp",[p])
    def test_script_plan(self):
        s={"id":"Quest","stages":[{"index":0,"actions":[{"op":"display","index":10,"value":True}]},{"index":10}],"objectives":[{"index":10}],"topics":[{"id":"Talk","responses":[{"end":[{"op":"stage","index":10}]}]}]}
        r=plan(s);self.assertFalse(r["compiled"]);self.assertEqual(r["scripts"][0]["source"],"SetObjectiveDisplayed Quest 10 1\n")
        self.assertEqual(r["scripts"][1]["source"],"SetStage Quest 10\n")
        s["stages"][0]["actions"]=[{"op":"stage","index":0}]
        with self.assertRaises(ValueError):plan(s)
