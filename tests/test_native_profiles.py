import unittest
from chimster.native_profiles import RuntimeSlots, Tes3Key, inspect_profile
from chimster.record_graph import Identity, Slots

class NativeProfileTests(unittest.TestCase):
    def test_runtime_reordering(self):
        a = RuntimeSlots("skyrim-se", ["A.esm", "B.esp"], ["C.esl", "D.esl"])
        b = RuntimeSlots("skyrim-se", ["B.esp", "A.esm"], ["D.esl", "C.esl"])
        for raw, expected in [(0x01000800, 0x00000800), (0xfe001800, 0xfe000800)]:
            self.assertEqual(b.encode(a.decode(raw)), expected)
        self.assertEqual(a.decode(0), None)
        with self.assertRaises(ValueError):
            a.decode(0xff000001)
        with self.assertRaises(ValueError):
            a.encode(Identity("C.esl", 0x1000))

    def test_profile_isolation(self):
        parts = [(b"LNAM", bytes(4))]
        self.assertEqual(inspect_profile("skyrim", "FLST", parts, Slots("A.esp")), ([], (0,)))
        with self.assertRaises(ValueError):
            RuntimeSlots("morrowind")
        with self.assertRaises(ValueError):
            RuntimeSlots("oblivion", light=["A.esl"])

    def test_tes3_named_key(self):
        self.assertEqual(Tes3Key("NPC_", "Example"), Tes3Key("NPC_", "example"))
        self.assertNotEqual(Tes3Key("NPC_", "Example"), Tes3Key("CREA", "example"))
