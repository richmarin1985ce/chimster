import unittest
import struct
import zlib
from chimster.native_parser import parse, subrecords
from chimster.native_serialization import serialize
from chimster.native_edit import edit_reference
from chimster.record_graph import Slots, Identity

class NativeRoundtrip(unittest.TestCase):
    def test_compressed_edit(self):
        raw=struct.pack("<4sHI",b"NAME",4,1)+b"TEST\x03\x00abc"
        payload=struct.pack("<I",len(raw))+zlib.compress(raw)
        data=struct.pack("<4sIIIII",b"REFR",len(payload),0x40000,3,0,0)+payload
        nodes=parse("new-vegas",data)
        self.assertEqual(serialize("new-vegas",nodes),data)
        slots=Slots("a.esp")
        target=Identity("a.esp",2)
        edited=edit_reference("new-vegas",nodes[0],slots,0,Identity("a.esp",1),target,{target:"STAT"})
        self.assertEqual(list(subrecords("new-vegas",edited)),[(b"NAME",struct.pack("<I",2)),(b"TEST",b"abc")])

    def test_vr_structural_inspection(self):
        from chimster.native_catalog import inspect_node
        raw=struct.pack("<4sHI",b"NAME",4,1)
        data=struct.pack("<4sIIIII",b"REFR",len(raw),0,3,0,0)+raw
        for profile in ("skyrim-vr","fallout4-vr"):
            node=parse(profile,data)[0]
            row=inspect_node(profile,node,Slots("a.esp"))
            self.assertEqual(row["key"],Identity("a.esp",3))
            self.assertEqual(row["edges"],[])
            self.assertEqual(row["opaque"],[0])
            with self.assertRaises(ValueError):
                edit_reference(profile,node,Slots("a.esp"),0,Identity("a.esp",1),None,{})

    def test_null_perk_target_is_typed(self):
        parts=[(b"EDID",b"P\0"),(b"FULL",b"P\0"),(b"DESC",b"P\0"),
               (b"DATA",bytes(5)),(b"PRKE",bytes([1,0,0])),
               (b"DATA",bytes(4)),(b"PRKF",b"")]
        raw=b"".join(struct.pack("<4sH",tag,len(value))+value for tag,value in parts)
        node=parse("new-vegas",struct.pack("<4sIIIII",b"PERK",len(raw),0,3,0,0)+raw)[0]
        slots=Slots("a.esp")
        target=Identity("a.esp",2)
        with self.assertRaises(ValueError):
            edit_reference("new-vegas",node,slots,5,None,target,{target:"MISC"})
        edited=edit_reference("new-vegas",node,slots,5,None,target,{target:"SPEL"})
        self.assertEqual(list(subrecords("new-vegas",edited))[5][1],struct.pack("<I",2))

    def test_remap_snapshot(self):
        from chimster.native_remap_plan import plan, apply
        a=Slots("a.esp",["b.esm","c.esm"])
        b=Slots("a.esp",["c.esm","b.esm"])
        parts=[(b"LNAM",struct.pack("<I",1))]
        proposal=plan("new-vegas","FLST",parts,a,b)
        self.assertTrue(proposal["applicable"])
        self.assertEqual(apply(parts,proposal),[(b"LNAM",struct.pack("<I",0x01000001))])
        with self.assertRaises(ValueError):
            apply(parts+[(b"ZZZZ",b"x")],proposal)
        self.assertFalse(plan("morrowind","STAT",[],None,None)["applicable"])
