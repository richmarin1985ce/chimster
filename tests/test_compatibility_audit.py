import struct
import unittest
from chimster.native_profiles import PROFILES,RuntimeSlots
from chimster.compatibility_audit import audit

ACTIVE=("morrowind","oblivion","fallout3","new-vegas","skyrim","skyrim-se","skyrim-vr","fallout4","fallout4-vr")
def fixture(profile):
    p=PROFILES[profile]
    tes3=p.family=="TES3"
    raw=bytes(300 if tes3 else 12)
    payload=struct.pack("<4sI" if tes3 else "<4sH",b"HEDR",len(raw))+raw
    return struct.pack("<4sI",b"TES3" if tes3 else b"TES4",len(payload))+bytes(p.record_header-8)+payload

class CompatibilityTests(unittest.TestCase):
    def test_active_profiles(self):
        for profile in ACTIVE:
            with self.subTest(profile=profile):
                result=audit(profile,fixture(profile))
                self.assertTrue(result["structural_valid"])
                self.assertFalse(result["retail_verified"])
                self.assertFalse(result["game_identity_verified"])
    def test_truncation(self):
        for profile in ACTIVE:
            with self.subTest(profile=profile):
                with self.assertRaises(ValueError):audit(profile,fixture(profile)[:-1])
    def test_vr_runtime_guard(self):
        for profile in ("skyrim-vr","fallout4-vr"):
            with self.assertRaises(ValueError):RuntimeSlots(profile)
