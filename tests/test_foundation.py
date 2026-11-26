import unittest
from chimster.formats import pack_fuz, unpack_fuz, encode_strings, decode_strings
from chimster.fragments import Fragment, inventory
from chimster.workspace import reload_guidance

class FoundationTests(unittest.TestCase):
    def test_strings(self):
        for kind in ("STRINGS", "DLSTRINGS", "ILSTRINGS"):
            data = {1: "Hello", 9: "café", 20: ""}
            self.assertEqual(decode_strings(encode_strings(data, kind), kind), data)
    def test_bad_strings(self):
        with self.assertRaises(ValueError):
            decode_strings(b"abc")
    def test_fuz(self):
        self.assertEqual(unpack_fuz(pack_fuz(b"lip", b"audio")), (1,b"lip",b"audio"))
    def test_bad_fuz(self):
        with self.assertRaises(ValueError):
            unpack_fuz(b"FUZE")
    def test_fragments(self):
        f = Fragment("mod.esp","000123","quest","stage10:0","QF_Test","Fragment_0","scripts/QF_Test.psc")
        self.assertIn("Fragment_0", inventory([f]))
        with self.assertRaises(ValueError):
            inventory([f,f])
    def test_reload(self):
        self.assertIn("reloadlua", reload_guidance("openmw"))
        self.assertIn("Restart", reload_guidance("unknown"))

if __name__ == "__main__":
    unittest.main()
