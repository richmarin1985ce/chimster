import unittest
from chimster.formids import FormIDs
from chimster.record_schema import fields
class SharedRecordTests(unittest.TestCase):
    def test_reservation(self):
        a=FormIDs("P.esp");b=FormIDs("P.esp")
        a.reserve(["STAT/z","STAT/a"]);b.reserve(["STAT/a","STAT/z"])
        self.assertEqual(a.get("STAT/z"),b.get("STAT/z"))
        self.assertEqual(a.get("STAT/a"),b.get("STAT/a"))
        c=FormIDs("P.esp",a.snapshot());c.reserve(["STAT/new"])
        self.assertEqual(c.get("STAT/a"),a.entries["STAT/a"])
        self.assertGreater(c.get("STAT/new"),a.entries["STAT/z"])
    def test_reference_inspection(self):
        row=fields("NPC_",None,[(b"RNAM",bytes([0,8,0,1]))])[0]
        self.assertEqual(row["reference"]["raw_formid"],0x01000800)
        self.assertEqual(row["reference"]["expected_types"],["RACE"])
        self.assertFalse(row["writable"])
