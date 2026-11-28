import io,struct,unittest
from chimster import dds_texture,ba2_texture,ba2_texture_writer

def fixture():
    levels=[bytes([face*2+mip])*size for face in range(6) for mip,size in enumerate((32,8))]
    return (b"DDS "+struct.pack("<18I",124,0xa1007,8,8,32,0,2,*([0]*11))
        +struct.pack("<II4s5I",32,4,b"DX10",0,0,0,0,0)
        +struct.pack("<5I",0x401008,0xfe00,0,0,0)
        +struct.pack("<5I",71,3,4,1,0)+b"".join(levels)),levels

class CubemapTests(unittest.TestCase):
    def test_faces(self):
        raw,levels=fixture()
        self.assertEqual(dds_texture.parse(raw)["levels"],levels)
        for version in (1,7,8):
            for compress in (False,True):
                with self.subTest(version=version,compress=compress):
                    stream=io.BytesIO(ba2_texture_writer.build([("textures/cube.dds",raw)],version=version,compress=compress))
                    entry=ba2_texture.directory(stream)["textures/cube.dds"]
                    self.assertEqual(entry["flags"]&1,1)
                    self.assertEqual(len(entry["chunks"]),1)
                    decoded=dds_texture.parse(ba2_texture.read(stream,entry))
                    self.assertTrue(decoded["cubemap"])
                    self.assertEqual(decoded["levels"],levels)
    def test_incomplete(self):
        raw,_=fixture()
        with self.assertRaises(ValueError):dds_texture.parse(raw[:-8])
    def test_partial_faces(self):
        raw,_=fixture()
        data=bytearray(raw)
        struct.pack_into("<I",data,112,0x600)
        with self.assertRaises(ValueError):dds_texture.parse(data)
    def test_array_rejected(self):
        raw,_=fixture()
        data=bytearray(raw)
        struct.pack_into("<I",data,140,2)
        with self.assertRaises(ValueError):dds_texture.parse(data)
