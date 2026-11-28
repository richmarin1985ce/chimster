import io,struct,unittest
from chimster import ba2_writer,ba2_general,ba2_texture_writer,ba2_texture,dds_texture
from chimster.ba2_hash import prepare

def texture():
    return (b"DDS "+struct.pack("<18I",124,0x81007,4,4,8,0,1,*([0]*11))
        +struct.pack("<II4s5I",32,4,b"DX10",0,0,0,0,0)
        +struct.pack("<5I",0x1000,0,0,0,0)
        +struct.pack("<5I",71,3,0,1,0)+b"12345678")

class VersionTests(unittest.TestCase):
    def test_versions(self):
        for version in (1,7,8):
            for compress in (False,True):
                with self.subTest(version=version,compress=compress):
                    raw=b"A"*4096
                    general=ba2_writer.build(prepare([("meshes/a.nif",raw)]),version=version,compress=compress)
                    self.assertEqual(struct.unpack_from("<I",general,4)[0],version)
                    stream=io.BytesIO(general)
                    self.assertEqual(ba2_general.read(stream,ba2_general.directory(stream)["meshes/a.nif"]),raw)
                    dds=texture()
                    archive=ba2_texture_writer.build([("textures/a.dds",dds)],version=version,compress=compress)
                    self.assertEqual(struct.unpack_from("<I",archive,4)[0],version)
                    stream=io.BytesIO(archive)
                    self.assertEqual(dds_texture.parse(ba2_texture.read(stream,ba2_texture.directory(stream)["textures/a.dds"])),dds_texture.parse(dds))
    def test_unsupported(self):
        for version in (0,2,3,9):
            with self.assertRaises(ValueError):
                ba2_writer.build([],version=version)
            with self.assertRaises(ValueError):
                ba2_texture_writer.build([],version=version)
