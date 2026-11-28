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

    def test_compression(self):
        for version in (103,104,105):
            with self.subTest(version=version):
                if version==105:
                    try:import lz4.frame
                    except ImportError:continue
                data=b"A"*4096
                stream=io.BytesIO(build([("meshes/a.nif",data),("meshes/b.nif",b"x")],version=version,compress=True))
                index=directory(stream)
                self.assertTrue(index["meshes/a.nif"][2])
                self.assertFalse(index["meshes/b.nif"][2])
                self.assertEqual(read(stream,index["meshes/a.nif"]),data)
                self.assertEqual(read(stream,index["meshes/b.nif"]),b"x")
