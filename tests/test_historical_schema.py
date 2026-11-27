import unittest,struct
from chimster.historical_schema import SchemaRegistry, remap_group_label, check_group_owner
from chimster.record_graph import Slots,Identity
class HistoricalSchemaTests(unittest.TestCase):
    def test_inheritance(self):
        r=SchemaRegistry();r.register("base",changes={"a":1,"b":2})
        r.register("next","base",{"a":3,"b":None,"c":4})
        r.register("branch","base",{"d":5})
        self.assertEqual(r.fields("next"),{"a":3,"c":4})
        self.assertEqual(r.fields("branch"),{"a":1,"b":2,"d":5})
    def test_group_labels(self):
        a=Slots("p.esp",["a.esm","b.esm"]);b=Slots("p.esp",["b.esm","a.esm"])
        raw=struct.pack("<I",0x800)
        self.assertEqual(remap_group_label(6,raw,a,b),struct.pack("<I",0x01000800))
        for k in (0,2,3,4,5):self.assertEqual(remap_group_label(k,raw,a,b),raw)
        check_group_owner(6,raw,a,{Identity("a.esm",0x800):"CELL"})
        with self.assertRaises(ValueError):check_group_owner(6,raw,a,{})
        with self.assertRaises(ValueError):remap_group_label(99,raw,a,b)
