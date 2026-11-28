import io,tempfile,unittest
from pathlib import Path
from chimster.tes3_bsa_writer import build
from chimster.tes3_bsa import directory,read
from chimster.archive_packaging import package_tes3

class TES3WriterTests(unittest.TestCase):
    def test_roundtrip(self):
        rows=[("Meshes/A.nif",b"abc"),("Textures/B.dds",b"def")]
        stream=io.BytesIO(build(rows))
        index=directory(stream)
        for name,data in rows:
            self.assertEqual(read(stream,index[name.lower()]),data)
    def test_publication(self):
        with tempfile.TemporaryDirectory() as root:
            target=Path(root)/"test.bsa"
            self.assertTrue(package_tes3(target,[("a.nif",b"abc")])["roundtrip_verified"])
            with self.assertRaises(FileExistsError):
                package_tes3(target,[("b.nif",b"def")])
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            build([("A.nif",b"a"),("a.nif",b"b")])
