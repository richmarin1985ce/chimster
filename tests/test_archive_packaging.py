import tempfile,unittest
from pathlib import Path
from chimster.archive_packaging import package
from chimster.archive_reader import read

class PackagingTests(unittest.TestCase):
    def test_publish(self):
        with tempfile.TemporaryDirectory() as root:
            target=Path(root)/"mod.ba2"
            rows=[("meshes/test.nif",b"A"*4096,1,2)]
            result=package(target,rows)
            self.assertTrue(result["roundtrip_verified"])
            self.assertFalse(result["retail_verified"])
            self.assertEqual(read(target,"meshes/test.nif"),rows[0][1])
            original=target.read_bytes()
            with self.assertRaises(FileExistsError):
                package(target,[("other.nif",b"other",3,4)])
            self.assertEqual(target.read_bytes(),original)
            self.assertEqual(list(Path(root).iterdir()),[target])
    def test_invalid_destination(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                package(Path(root)/"mod.zip",[("a.nif",b"a",1,2)])
            self.assertEqual(list(Path(root).iterdir()),[])
