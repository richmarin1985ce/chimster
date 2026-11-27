import unittest
import struct
import zlib
from chimster.native_parser import parse, subrecords
from chimster.native_serialization import serialize
from chimster.native_edit import edit_reference
from chimster.record_graph import Slots, Identity

class NativeRoundtrip(unittest.TestCase):
    def test_compressed_edit(self):
        raw=struct.pack("<4sHI",b"NAME",4,1)+b"TEST\x03\x00abc"
        payload=struct.pack("<I",len(raw))+zlib.compress(raw)
        data=struct.pack("<4sIIIII",b"REFR",len(payload),0x40000,3,0,0)+payload
        nodes=parse("new-vegas",data)
        self.assertEqual(serialize("new-vegas",nodes),data)
        slots=Slots("a.esp")
        target=Identity("a.esp",2)
        edited=edit_reference("new-vegas",nodes[0],slots,0,Identity("a.esp",1),target,{target:"STAT"})
        self.assertEqual(list(subrecords("new-vegas",edited)),[(b"NAME",struct.pack("<I",2)),(b"TEST",b"abc")])
