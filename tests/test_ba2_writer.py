import io,unittest
from chimster.ba2_writer import build
from chimster.ba2_general import directory,read

class WriterTests(unittest.TestCase):
    def test_roundtrip(self):
        stream=io.BytesIO(build([("meshes/a.nif",b"synthetic",1,2),("textures/b.dds",b"test",3,4)]))
        entries=directory(stream)
        self.assertEqual(read(stream,entries["meshes/a.nif"]),b"synthetic")
        self.assertEqual(read(stream,entries["textures/b.dds"]),b"test")
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            build([("A.nif",b"a",1,2),("a.nif",b"b",1,2)])
    def test_budget(self):
        with self.assertRaises(ValueError):
            build([("a.nif",b"a",1,2)],limit=24)
    def test_compressed(self):
        data=b"A"*4096
        stream=io.BytesIO(build([("a.nif",data,1,2)],compress=True))
        entry=directory(stream)["a.nif"]
        self.assertGreater(entry[1],0)
        self.assertEqual(read(stream,entry),data)
