import unittest
import struct
from chimster.record_graph import Identity, Slots, Graph, remap_fields
class GraphTests(unittest.TestCase):
    def test_reorder_add_remove(self):
        a=Slots("P.esp",["A.esm","B.esm"])
        b=Slots("P.esp",["B.esm","C.esm","A.esm"])
        self.assertEqual(a.remap(0x800,b),0x02000800)
        self.assertEqual(a.remap(0x01000800,b),0x800)
        self.assertEqual(a.remap(0x02000800,b),0x03000800)
        self.assertEqual(a.remap(0,b),0)
        with self.assertRaises(ValueError):a.remap(0x01000800,Slots("P.esp",["A.esm"]))
    def test_unknown_blocks_remapping(self):
        a=Slots("P.esp",["A.esm"]);b=Slots("P.esp")
        parts=[(b"UNKN",b"opaque")]
        self.assertEqual(remap_fields("FLST",parts,a,a),parts)
        with self.assertRaises(ValueError):remap_fields("FLST",parts,a,b)
    def test_embedded_offset_preserves_other_bytes(self):
        a=Slots("P.esp",["A.esm"]);b=Slots("P.esp",["B.esm","A.esm"])
        raw=struct.pack("<h2sIh2s",3,b"ab",0x800,4,b"cd")
        result=remap_fields("LVLI",[(b"LVLO",raw)],a,b)[0][1]
        self.assertEqual(result[:4],raw[:4]);self.assertEqual(result[8:],raw[8:])
        self.assertEqual(struct.unpack_from("<I",result,4)[0],0x01000800)
    def test_graph(self):
        a=Slots("P.esp");owner=Identity("P.esp",0x800);target=Identity("P.esp",0x801)
        g=Graph({owner:{"signature":"NPC_"},target:{"signature":"VTYP"}})
        g.add(owner,"NPC_",[(b"RNAM",struct.pack("<I",0x801))],a)
        self.assertEqual(g.issues[0][-1],"wrong-type")
        self.assertFalse(g.deletion_review(target)["safe"])
        self.assertFalse(g.deletion_review(owner)["safe"])
        self.assertEqual(g.deletion_review(owner)["unindexed_records"],[target])
        g.add(target,"VTYP",[(b"EDID",b"Voice\0"),(b"DNAM",b"\0")],a)
        self.assertTrue(g.deletion_review(owner)["safe"])
        g.add(target,"VTYP",[(b"UNKN",b"x")],a)
        self.assertFalse(g.deletion_review(owner)["safe"])
