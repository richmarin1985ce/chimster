import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fnv_quest import export
from chimster.fnv_records import scan
class NativeQuestTests(unittest.TestCase):
    def test_records(self):
        s={"schema":1,"id":"TestQuest","title":"Test","stages":[{"index":0,"log":"Start"},{"index":10,"log":"End","complete":True}],"objectives":[{"index":10,"text":"Reach the gate"}],"topics":[{"id":"Ask","prompt":"Ask","responses":[{"text":"Hello","choices":["Leave"]}]},{"id":"Leave","prompt":"Leave","responses":[{"text":"Goodbye","goodbye":True}]}]}
        with TemporaryDirectory() as d:
            p=Path(d)/"Quest.esp";r=export(s,p)
            self.assertEqual(r["responses"],2)
            self.assertEqual([x["signature"] for x in scan(p)["records"]],["DIAL","INFO","DIAL","INFO","QUST"])
            s["topics"][0]["responses"][0]["choices"]=["Missing"]
            with self.assertRaises(ValueError):export(s,Path(d)/"Bad.esp")

    def test_condition(self):
        import struct
        from chimster.fnv_quest import conditions
        from chimster.fnv_records import subs
        parts=list(subs(conditions([{"stage":10,"done":True}],0x800,{10})))
        self.assertEqual(parts[0][0],b"CTDA")
        self.assertEqual(struct.unpack("<B3xfIIIII",parts[0][1]),(0,1.,59,0x800,10,0,0))
        with self.assertRaises(ValueError):conditions([{"stage":20,"done":True}],0x800,{10})

    def test_multiline_and_flags(self):
        import struct
        from chimster.fnv_records import HEADER,subs
        s={"schema":1,"id":"Quest","title":"Quest","start_enabled":True,"repeat_topics":True,"delay":2,"stages":[{"index":0,"log":"Start"},{"index":10,"log":"End","complete":True,"conditions":[{"stage":0,"done":True}]}],"topics":[{"id":"Talk","prompt":"Talk","top_level":True,"responses":[{"lines":[{"text":"First"},{"text":"Second","emotion":5,"emotion_value":40}],"flags":["say_once"],"next_speaker":1,"prompt":"Ask"}]}]}
        with TemporaryDirectory() as d:
            p=Path(d)/"Quest.esp";export(s,p)
            recs=scan(p)["records"]
            with p.open("rb") as f:
                def fields(sig):
                    r=next(x for x in recs if x["signature"]==sig)
                    f.seek(r["offset"]);_,n,*_=HEADER.unpack(f.read(24));return list(subs(f.read(n)))
                info=fields("INFO")
                self.assertEqual(struct.unpack("<BBH",dict(info)[b"DATA"]),(0,1,4))
                self.assertEqual([v[12] for k,v in info if k==b"TRDT"],[1,2])
                self.assertEqual([v for k,v in info if k==b"NAM1"],[b"First\0",b"Second\0"])
                self.assertEqual(dict(fields("QUST"))[b"DATA"][0],5)

    def test_master_insertion_preserves_dialogue_and_conditions(self):
        import struct
        from chimster.record_project import export as records
        from chimster.master_remap import reorder
        from chimster.native_parser import parse,subrecords
        from chimster.record_graph import Slots
        from chimster.quest_remap_schema import fields
        spec={"schema":1,"id":"Quest","title":"Quest","stages":[
            {"index":0,"log":"Start"},
            {"index":10,"log":"End","conditions":[{"stage":0,"done":True}]}],
            "topics":[{"id":"Talk","prompt":"Talk","responses":[
                {"text":"First","choices":["Leave"],"conditions":[{"stage":0,"done":True}]},
                {"text":"Second"}]},
                {"id":"Leave","prompt":"Leave","responses":[{"text":"Bye","goodbye":True}]}]}
        with TemporaryDirectory() as d:
            root=Path(d);master=root/"A.esp";source=root/"Quest.esp"
            records({"schema":1,"records":[{"id":"Global","type":"GLOB",
                     "fields":{"kind":"f","value":1.}}]},master)
            export(spec,source)
            stage=root/"stage";stage.mkdir();dest=stage/source.name
            report=reorder(source,dest,[master],allow_set_change=True)
            self.assertEqual(report["changed_group_owners"],2)
            self.assertGreater(report["changed_embedded_references"],6)
            def identities(path):
                slots=Slots(path.name,scan(path)["masters"])
                def walk(nodes):
                    for node in nodes:
                        if node.signature in (b"QUST",b"DIAL",b"INFO"):
                            parts=list(subrecords("new-vegas",node))
                            yield [(i,offset,slots.decode(struct.unpack_from("<I",parts[i][1],offset)[0]))
                                   for i,offset,_ in fields(node.signature,parts)]
                        yield from walk(node.children)
                return list(walk(parse("new-vegas",path.read_bytes())))
            self.assertEqual(identities(source),identities(dest))

    def test_nonempty_script_refused(self):
        from chimster.master_remap import reorder
        spec={"schema":1,"id":"Quest","title":"Quest","stages":[
            {"index":0,"log":"Start","actions":[{"op":"stage","index":10}]},
            {"index":10,"log":"End"}]}
        with TemporaryDirectory() as d:
            root=Path(d);source=root/"Quest.esp"
            export(spec,source,script_draft=True)
            stage=root/"stage";stage.mkdir();dest=stage/source.name
            with self.assertRaisesRegex(ValueError,"nonempty script"):
                reorder(source,dest,[])
            self.assertFalse(dest.exists())

    def test_unsupported_condition_refused(self):
        import struct
        from chimster.quest_remap_schema import fields
        from chimster.fnv_quest import empty_script
        from chimster.fnv_records import subs
        parts=[(b"EDID",b"Q\0"),(b"FULL",b"Q\0"),(b"DATA",bytes(8)),
               (b"CTDA",struct.pack("<B3xfIIIII",0,1.,999,0x800,0,0,0)),
               (b"INDX",bytes(2)),(b"QSDT",bytes(1)),(b"CNAM",b"S\0")]
        parts+=list(subs(empty_script()))
        with self.assertRaisesRegex(ValueError,"unsupported condition"):
            fields(b"QUST",parts)

    def test_shared_native_quest_and_world_validation(self):
        from chimster.native_quests import inspect,validate
        from chimster.world_validator import validate as validate_world
        from chimster.record_graph import Slots
        spec={"schema":1,"id":"Quest","title":"Quest",
              "stages":[{"index":0,"log":"Start"},{"index":10,"log":"End","conditions":[{"stage":0,"done":True}]}],
              "topics":[{"id":"Talk","prompt":"Talk","responses":[{"text":"First"},{"text":"Second"}]}]}
        with TemporaryDirectory() as d:
            path=Path(d)/"Quest.esp";export(spec,path)
            rows=list(inspect("new-vegas",path.read_bytes(),Slots(path.name)))
            self.assertEqual(list(validate(rows)),[])
            quest=next(r for r in rows if r["signature"]=="QUST")
            self.assertTrue(any(offset==12 for _,offset,_ in quest["typed_offsets"]))
            self.assertEqual(quest["opaque"],[])
            report=validate_world([path],quest_links=True)
            self.assertTrue(report["quest_links_checked"])
            self.assertTrue(report["valid"],report["issues"])
