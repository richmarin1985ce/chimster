import io,struct,unittest
from chimster.classic_bsa_writer import build
from chimster.classic_bsa import directory,read

class ClassicWriterTests(unittest.TestCase):
    def test_versions(self):
        rows=[("meshes/a.nif",b"abc"),("textures/b.dds",b"def"),("meshes/c.nif",b"ghi")]
        for version in (103,104,105):
            with self.subTest(version=version):
                raw=build(rows,version=version)
                self.assertEqual(struct.unpack_from("<I",raw,4)[0],version)
                stream=io.BytesIO(raw)
                index=directory(stream)
                self.assertEqual(len(index),len(rows))
                for name,data in rows:
                    self.assertEqual(read(stream,index[name]),data)
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            build([("meshes/a.nif",b"a"),("Meshes/A.nif",b"b")])
