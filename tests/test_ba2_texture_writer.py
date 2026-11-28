import io,struct,tempfile,unittest
from pathlib import Path
from chimster import ba2_texture,ba2_texture_writer,dds_texture
from chimster.archive_packaging import package_textures

def fixture():
    return (b"DDS "+struct.pack("<18I",124,0xa1007,16,16,128,0,2,*([0]*11))
        +struct.pack("<II4s5I",32,4,b"DX10",0,0,0,0,0)
        +struct.pack("<5I",0x401008,0,0,0,0)
        +struct.pack("<5I",71,3,0,1,0)+b"A"*128+b"B"*32)

class TextureWriterTests(unittest.TestCase):
    def test_roundtrip(self):
        raw=fixture()
        for compress in (False,True):
            stream=io.BytesIO(ba2_texture_writer.build([("textures/a.dds",raw)],compress=compress))
            index=ba2_texture.directory(stream)
            self.assertEqual(dds_texture.parse(ba2_texture.read(stream,index["textures/a.dds"])),dds_texture.parse(raw))
    def test_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"Mod - Textures.ba2"
            self.assertTrue(package_textures(target,[("textures/a.dds",fixture())])["roundtrip_verified"])
            with self.assertRaises(FileExistsError):
                package_textures(target,[("textures/a.dds",fixture())])
    def test_truncated(self):
        with self.assertRaises(ValueError):
            ba2_texture_writer.build([("textures/a.dds",fixture()[:-1])])
