import io,struct,zlib,unittest
from chimster import classic_bsa,ba2_general,tes3_bsa

class ArchiveTests(unittest.TestCase):
    def test_classic_member(self):
        data=b"synthetic asset"
        raw=b"\x03abc"+struct.pack("<I",len(data))+zlib.compress(data)
        self.assertEqual(classic_bsa.read(io.BytesIO(raw),(0,len(raw),True,104,True)),data)
        with self.assertRaises(ValueError):
            classic_bsa.read(io.BytesIO(raw),(0,len(raw),True,104,True),limit=2)
    def test_ba2(self):
        data=b"asset";packed=zlib.compress(data);name=b"meshes/a.nif"
        header=struct.pack("<4sI4sIQ",b"BTDX",1,b"GNRL",1,60+len(packed))
        row=struct.pack("<I4sIIQIII",0,b"nif\0",0,0,60,len(packed),len(data),0)
        stream=io.BytesIO(header+row+packed+struct.pack("<H",len(name))+name)
        entries=ba2_general.directory(stream)
        self.assertEqual(ba2_general.read(stream,entries["meshes/a.nif"]),data)
    def test_tes3(self):
        name=b"meshes/a.nif\0";data=b"asset"
        stream=io.BytesIO(struct.pack("<III",256,12+len(name),1)+struct.pack("<III",len(data),0,0)+name+b"\0"*8+data)
        entries=tes3_bsa.directory(stream)
        self.assertEqual(tes3_bsa.read(stream,entries["meshes/a.nif"]),data)
    def test_bad_embedded_name(self):
        with self.assertRaises(ValueError):
            classic_bsa.read(io.BytesIO(b"\xffx"),(0,2,False,104,True))
