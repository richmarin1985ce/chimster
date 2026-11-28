import struct,tempfile,unittest
from pathlib import Path
from chimster.ba2_split import split,package_pair
from chimster.archive_reader import read

def texture():
    return (b"DDS "+struct.pack("<18I",124,0x81007,4,4,8,0,1,*([0]*11))
        +struct.pack("<II4s5I",32,4,b"DX10",0,0,0,0,0)
        +struct.pack("<5I",0x1000,0,0,0,0)
        +struct.pack("<5I",71,3,0,1,0)+b"12345678")

class SplitTests(unittest.TestCase):
    def test_pair(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            result=package_pair(root,"Example",[("meshes/a.nif",b"mesh"),("textures/a.dds",texture())],version=8)
            self.assertEqual(result["general_members"],1)
            self.assertEqual(result["texture_members"],1)
            self.assertEqual(read(root/"Example - Main.ba2","meshes/a.nif"),b"mesh")
            self.assertEqual(read(root/"Example - Textures.ba2","textures/a.dds"),texture())
    def test_invalid_texture(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                package_pair(folder,"Example",[("meshes/a.nif",b"mesh"),("textures/a.dds",b"bad")])
            self.assertEqual(list(Path(folder).iterdir()),[])
    def test_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            existing=root/"Example - Textures.ba2"
            existing.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                package_pair(root,"Example",[("meshes/a.nif",b"mesh"),("textures/a.dds",texture())])
            self.assertEqual(existing.read_bytes(),b"original")
            self.assertFalse((root/"Example - Main.ba2").exists())
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            split([("meshes/a.nif",b"a"),("Meshes/A.nif",b"b")])
    def test_single_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            result=package_pair(folder,"Example",[("meshes/a.nif",b"a")])
            self.assertEqual(len(result["archives"]),1)
