import io,struct,unittest
from chimster.ba2_texture import read

class TextureTests(unittest.TestCase):
    def test_bc1(self):
        raw=b"\0"*8
        entry={"width":4,"height":4,"mips":1,"dxgi_format":71,"flags":0,"chunks":[{"offset":0,"packed":0,"unpacked":8,"first_mip":0,"last_mip":0}]}
        dds=read(io.BytesIO(raw),entry)
        self.assertEqual(len(dds),156)
        self.assertEqual(dds[:4],b"DDS ")
        self.assertEqual(struct.unpack_from("<I",dds,128)[0],71)
        self.assertEqual(dds[148:],raw)
        entry["mips"]=2
        with self.assertRaises(ValueError):read(io.BytesIO(raw),entry)
