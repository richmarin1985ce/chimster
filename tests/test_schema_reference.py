import struct
import unittest
from chimster.record_graph import Slots, Identity
from chimster.schema_reference import ReferenceIndex, inspect

class SchemaReferenceTests(unittest.TestCase):
    def test_cycle_and_replacement(self):
        slots = Slots("Example.esp")
        a, b = Identity("Example.esp", 1), Identity("Example.esp", 2)
        index = ReferenceIndex()
        index.add(a, "FLST", [(b"LNAM", struct.pack("<I", 2))], slots)
        index.add(b, "FLST", [(b"LNAM", struct.pack("<I", 1))], slots)
        self.assertEqual(index.closure(a), [b])
        self.assertEqual(index.closure(a, reverse=True), [b])
        index.add(b, "FLST", [], slots)
        self.assertEqual(index.closure(a, reverse=True), [])
        self.assertEqual(index.closure(a), [b])

    def test_opaque_and_missing(self):
        slots = Slots("Example.esp")
        a = Identity("Example.esp", 1)
        b = Identity("Example.esp", 2)
        index = ReferenceIndex()
        index.add(a, "FLST", [(b"LNAM", struct.pack("<I", 2)), (b"ZZZZ", b"")], slots)
        self.assertEqual(index.review(a)["unindexed"], [b])
        self.assertEqual(index.review(a)["opaque"], [a])

    def test_ammo_multiple_offsets(self):
        slots = Slots("Example.esp")
        data = bytearray(20)
        struct.pack_into("<I", data, 4, 2)
        struct.pack_into("<I", data, 12, 3)
        parts = [(b"EDID", b"A\0"), (b"OBND", bytes(12)),
                 (b"FULL", b"A\0"), (b"MODL", b"A\0"),
                 (b"DATA", bytes(13)), (b"DAT2", bytes(data))]
        edges, opaque = inspect("AMMO", parts, slots)
        self.assertEqual(opaque, ())
        self.assertEqual([e.offset for e in edges], [4, 12])
        self.assertEqual([e.target.local for e in edges], [2, 3])

    def test_perk_conditional_types(self):
        from chimster.native_catalog import references
        from chimster.record_graph import Graph
        slots = Slots("Example.esp")
        owner, target = Identity("Example.esp", 1), Identity("Example.esp", 2)
        for effect, expected, payload in [
            (0, "QUST", struct.pack("<IB3x", 2, 10)),
            (1, "SPEL", struct.pack("<I", 2)),
        ]:
            parts = [(b"EDID", b"P\0"), (b"FULL", b"P\0"),
                     (b"DESC", b"P\0"), (b"DATA", bytes(5)),
                     (b"PRKE", bytes([effect, 0, 0])),
                     (b"DATA", payload), (b"PRKF", b"")]
            edges, opaque = references("new-vegas", "PERK", iter(parts), slots)
            self.assertEqual(opaque, [])
            self.assertEqual(edges, [(5, 0, target, (expected,))])
            graph = Graph({owner: {"signature": "PERK"}, target: {"signature": "MISC"}})
            graph.add(owner, "PERK", parts, slots)
            self.assertEqual(graph.issues[0][-1], "wrong-type")

    def test_consumable_reference_types(self):
        slots = Slots("Example.esp")
        parts = [(b"EDID", b"A\0"), (b"OBND", bytes(12)),
                 (b"FULL", b"A\0"), (b"MODL", b"A\0"),
                 (b"ETYP", bytes(4)), (b"DATA", bytes(4)),
                 (b"ENIT", struct.pack("<iB3xIfI", 1, 0, 2, 0., 3)),
                 (b"EFID", struct.pack("<I", 4)), (b"EFIT", bytes(20))]
        edges, opaque = inspect("ALCH", parts, slots)
        self.assertEqual(opaque, ())
        self.assertEqual([e.expected_types for e in edges], [("SPEL",), ("SOUN",), ("MGEF",)])

    def test_generated_quest_and_world_edges(self):
        from chimster.native_catalog import references
        slots=Slots("Example.esp")
        topic=[(b"EDID",b"Topic\0"),(b"QSTI",struct.pack("<I",2)),
               (b"FULL",b"Talk\0"),(b"PNAM",bytes(4)),(b"DATA",bytes(2))]
        edges,opaque=references("new-vegas","DIAL",topic,slots)
        self.assertEqual(opaque,[])
        self.assertEqual(edges,[(1,0,Identity("Example.esp",2),("QUST",))])
        ref=[(b"NAME",struct.pack("<I",3)),(b"XSCL",struct.pack("<f",1.)),(b"DATA",bytes(24))]
        edges,opaque=references("new-vegas","REFR",ref,slots)
        self.assertEqual(opaque,[])
        self.assertEqual(edges,[(0,0,Identity("Example.esp",3),("STAT","BOOK","NOTE"))])
        _,opaque=references("new-vegas","REFR",ref+[(b"ZZZZ",b"x")],slots)
        self.assertIn(3,opaque)
