import unittest
import struct
from chimster.tes3_ai_packages import create,decode,edit,inspect,manage
from chimster.native_transactions import History,revision
from chimster.native_parser import parse,subrecords

def record(tag,parts):
    payload=b"".join(struct.pack("<4sI",k,len(v))+v for k,v in parts)
    return struct.pack("<4sIII",tag,len(payload),0,0)+payload

class Packages(unittest.TestCase):
    def test_layouts(self):
        for tag,size,props in [(b"AI_W",14,{"distance":512}),(b"AI_T",16,{"x":12.5}),(b"AI_F",48,{"target":"guard"}),(b"AI_E",48,{"target":"guard"}),(b"AI_A",33,{"target":"door"})]:
            with self.subTest(tag=tag):
                raw=create(tag,**props)
                self.assertEqual(len(raw),size)
                for k,v in props.items():self.assertEqual(decode(tag,raw)[k],v)
    def test_padding(self):
        raw=create(b"AI_T",x=1)[:-3]+b"xyz"
        self.assertEqual(edit(b"AI_T",raw,y=2)[-3:],b"xyz")
    def test_history(self):
        parts=[(b"NAME",b"guard\0"),(b"AI_F",create(b"AI_F",target="player")),(b"CNDT",b"Balmora\0"),(b"AI_W",create(b"AI_W",distance=128)),(b"ZZZZ",b"opaque")]
        data=record(b"TES3",[(b"HEDR",bytes(296)+struct.pack("<I",1))])+record(b"NPC_",parts)
        h=History("morrowind",data)
        moved=h.commit([{"kind":"ai_packages","index":1,"action":"move","package":0,"destination":1}],revision(data))
        rows=inspect(list(subrecords("morrowind",parse("morrowind",moved)[1])))
        self.assertEqual([r["tag"] for r in rows],[b"AI_W",b"AI_F"])
        self.assertEqual(rows[1]["cell"],"Balmora")
        self.assertEqual(h.undo(),data)
        self.assertEqual(h.redo(),moved)
        with self.assertRaises(ValueError):manage(moved,1,"remove",revision(data),package=0)
