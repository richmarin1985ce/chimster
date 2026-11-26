import unittest,struct
from chimster.remap_schema import rewrite
from chimster.fnv_records import subs
class RemapGameplayTests(unittest.TestCase):
    def test_container(self):
        p=[(b"EDID",b"Box\0"),(b"OBND",bytes(12)),(b"FULL",b"Box\0"),(b"MODL",b"box.nif\0"),(b"CNTO",struct.pack("<Ii",0x800,2)),(b"DATA",struct.pack("<Bf",2,1))]
        raw,n=rewrite(b"CONT",p,lambda v:v+0x1000000 if v else 0)
        self.assertEqual(n,1);self.assertEqual(dict(subs(raw))[b"CNTO"],struct.pack("<Ii",0x01000800,2))
        with self.assertRaises(ValueError):rewrite(b"CONT",p+[(b"ZZZZ",bytes(4))],lambda v:v)
    def test_perk(self):
        p=[(b"EDID",b"Perk\0"),(b"FULL",b"Perk\0"),(b"DESC",b"Text\0"),(b"DATA",bytes(5)),(b"PRKE",bytes([1,0,0])),(b"DATA",struct.pack("<I",0x800)),(b"PRKF",b"")]
        raw,n=rewrite(b"PERK",p,lambda v:v+0x1000000)
        self.assertEqual(n,1);self.assertEqual(list(subs(raw))[-2][1],struct.pack("<I",0x01000800))
