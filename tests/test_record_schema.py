import unittest,struct
from chimster.record_schema import encode,decode,fields
class SchemaTests(unittest.TestCase):
    def test_types(self):
        v={"flags":2,"skill":8,"value":25,"weight":.5}
        self.assertEqual(decode("book",encode("book",v)),v)
        self.assertEqual(decode("bounds",encode("bounds",[-1,-2,0,1,2,3])),[-1,-2,0,1,2,3])
        self.assertFalse(fields("STAT","Test",[(b"ZZZZ",b"x")])[0]["writable"])
        self.assertFalse(fields("STAT","Test",[(b"MODL",b"a.nif\0"),(b"MODL",b"b.nif\0")])[0]["writable"])
        with self.assertRaises(ValueError):encode("scale",0)
        with self.assertRaises(ValueError):encode("short_global",32768)
