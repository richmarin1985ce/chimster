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

    def test_active_profile_aliases_and_gates(self):
        from chimster.native_profiles import canonical_profile, active_profiles
        from chimster.compatibility_policy import capabilities, require
        self.assertEqual(canonical_profile("SkyrimAE"), "skyrim-se")
        self.assertEqual(canonical_profile("fallout4vr"), "fallout4-vr")
        self.assertEqual(len(active_profiles()), 9)
        self.assertEqual(capabilities("newvegas"), capabilities("new-vegas"))
        self.assertTrue(capabilities("skyrim-ae")["partial_reference_catalog"])
        self.assertFalse(capabilities("skyrim-ae")["typed_reference_schema"])
        self.assertFalse(capabilities("skyrimvr")["runtime_identity"])
        self.assertFalse(capabilities("oblivionremastered")["structural_read"])
        with self.assertRaises(ValueError):
            RuntimeSlots("oblivion-remastered")
        with self.assertRaises(ValueError):
            require("skyrim-vr", "runtime_identity")
        with self.assertRaises(ValueError):
            canonical_profile("starfield")
