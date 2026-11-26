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
