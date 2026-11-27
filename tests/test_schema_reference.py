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
