import hashlib
import struct
import unittest
from chimster.native_typed_edit import edit
from chimster.native_parser import parse, subrecords
from chimster.tes3_items import SCHEMAS

def record(sig,parts):
    payload=b"".join(struct.pack("<4sI",tag,len(v))+v for tag,v in parts)
    return struct.pack("<4sIII",sig,len(payload),0,0)+payload

class TypedTES3(unittest.TestCase):
    def roundtrip(self,sig,tag,raw,changes,expected):
        parts=[(b"NAME",b"fixture\0"),(tag,raw),(b"ZZZZ",b"opaque"),(tag,raw)]
        tail=record(b"MISC",[(b"NAME",b"other\0")])
        data=record(sig,parts)+tail
        rev=hashlib.sha256(data).hexdigest()
        out=edit("morrowind",data,(0,),tag,1,changes,rev)
        parts[-1]=(tag,expected)
        self.assertEqual(out,record(sig,parts)+tail)
        self.assertEqual(list(subrecords("morrowind",parse("morrowind",out)[0])),parts)
        with self.assertRaises(ValueError):
            edit("morrowind",out,(0,),tag,1,changes,rev)
        return data,rev

    def test_all_fixed_schemas(self):
        for (sig,tag),(fmt,keys) in SCHEMAS.items():
            with self.subTest(sig=sig,tag=tag):
                raw=bytes(struct.calcsize(fmt))
                key=next(k for k in keys if k!="unknown")
                values=[0]*len(keys);values[keys.index(key)]=1
                self.roundtrip(sig.encode(),tag.encode(),raw,{key:1},struct.pack(fmt,*values))

    def test_special_editors(self):
        cases=[
            (b"INGR",b"IRDT",bytes(56),{"value":5},struct.pack("<fi",0,5)+bytes(48)),
            (b"NPC_",b"NPDT",bytes(12),{"gold":15},bytes(8)+struct.pack("<i",15)),
            (b"NPC_",b"NPDT",bytes(52),{"gold":15},bytes(48)+struct.pack("<i",15)),
        ]
        for sig in (b"NPC_",b"CREA",b"CONT"):
            raw=struct.pack("<i32s",1,b"item")
            cases.append((sig,b"NPCO",raw,{"count":-3},struct.pack("<i", -3)+raw[4:]))
        for sig in (b"LEVI",b"LEVC"):
            cases.extend([(sig,b"INTV",b"\x01\x00",{"level":5},b"\x05\x00"),(sig,b"NNAM",b"\x00",{"chance":25},b"\x19")])
        for case in cases:
            with self.subTest(sig=case[0],tag=case[1]):self.roundtrip(*case)

    def test_invalid(self):
        data=record(b"LEVI",[(b"NNAM",b"\x00")])
        rev=hashlib.sha256(data).hexdigest()
        with self.assertRaises(ValueError):edit("morrowind",data,(0,),b"NNAM",0,{"chance":101},rev)
        with self.assertRaises(ValueError):edit("morrowind",data,(0,),b"NNAM",0,{"chance":10},"stale")
        with self.assertRaises(ValueError):edit("morrowind",data,(0,),b"NNAM",1,{"chance":10},rev)
