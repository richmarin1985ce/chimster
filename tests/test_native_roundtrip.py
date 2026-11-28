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

    def test_vr_structural_inspection(self):
        from chimster.native_catalog import inspect_node
        raw=struct.pack("<4sHI",b"NAME",4,1)
        data=struct.pack("<4sIIIII",b"REFR",len(raw),0,3,0,0)+raw
        for profile in ("skyrim-vr","fallout4-vr"):
            node=parse(profile,data)[0]
            row=inspect_node(profile,node,Slots("a.esp"))
            self.assertEqual(row["key"],Identity("a.esp",3))
            self.assertEqual(row["edges"],[])
            self.assertEqual(row["opaque"],[0])
            with self.assertRaises(ValueError):
                edit_reference(profile,node,Slots("a.esp"),0,Identity("a.esp",1),None,{})

    def test_null_perk_target_is_typed(self):
        parts=[(b"EDID",b"P\0"),(b"FULL",b"P\0"),(b"DESC",b"P\0"),
               (b"DATA",bytes(5)),(b"PRKE",bytes([1,0,0])),
               (b"DATA",bytes(4)),(b"PRKF",b"")]
        raw=b"".join(struct.pack("<4sH",tag,len(value))+value for tag,value in parts)
        node=parse("new-vegas",struct.pack("<4sIIIII",b"PERK",len(raw),0,3,0,0)+raw)[0]
        slots=Slots("a.esp")
        target=Identity("a.esp",2)
        with self.assertRaises(ValueError):
            edit_reference("new-vegas",node,slots,5,None,target,{target:"MISC"})
        edited=edit_reference("new-vegas",node,slots,5,None,target,{target:"SPEL"})
        self.assertEqual(list(subrecords("new-vegas",edited))[5][1],struct.pack("<I",2))

    def test_remap_snapshot(self):
        from chimster.native_remap_plan import plan, apply
        a=Slots("a.esp",["b.esm","c.esm"])
        b=Slots("a.esp",["c.esm","b.esm"])
        parts=[(b"LNAM",struct.pack("<I",1))]
        proposal=plan("new-vegas","FLST",parts,a,b)
        self.assertTrue(proposal["applicable"])
        self.assertEqual(apply(parts,proposal),[(b"LNAM",struct.pack("<I",0x01000001))])
        with self.assertRaises(ValueError):
            apply(parts+[(b"ZZZZ",b"x")],proposal)
        self.assertFalse(plan("morrowind","STAT",[],None,None)["applicable"])


class NativeTypedWorkbench(unittest.TestCase):
    @staticmethod
    def fixture(profile, localized=False, deleted=False):
        from chimster.native_profiles import PROFILES
        p=PROFILES[profile]
        tes3=p.family=="TES3"
        def record(sig,parts,form=0,flags=0):
            payload=b"".join(struct.pack("<4sI" if tes3 else "<4sH",tag,len(raw))+raw for tag,raw in parts)
            if tes3:header=struct.pack("<4sIII",sig,len(payload),0,flags)
            else:header=struct.pack("<4sIIII",sig,len(payload),flags,form,0)+bytes(p.record_header-20)
            return header+payload
        header=record(b"TES3" if tes3 else b"TES4",[],flags=0x80 if localized else 0)
        name=b"NAME" if tes3 else b"EDID"
        title=b"FNAM" if tes3 else b"FULL"
        misc=record(b"MISC",[(name,b"Object\0"),(title,b"Old\0"),(b"ZZZZ",b"opaque")],1,0x20 if deleted else 0)
        gmst=record(b"GMST",[(name,b"iExample\0"),(b"INTV" if tes3 else b"DATA",struct.pack("<i",7))],2)
        if not tes3:
            def group(sig,body):
                return struct.pack("<4sI4siI",b"GRUP",p.group_header+len(body),sig,0,0)+bytes(p.group_header-20)+body
            misc=group(b"MISC",misc)
            gmst=group(b"GMST",gmst)
        return header+misc+gmst, None if tes3 else Slots("fixture.esp")

    def test_cross_game_typed_fields_and_atomic_batch(self):
        from chimster.native_editor import NativeSession
        for profile in ("morrowind","oblivion","fallout3","new-vegas","skyrim","skyrim-se","fallout4"):
            with self.subTest(profile=profile):
                data,slots=self.fixture(profile)
                s=NativeSession(profile,data,slots)
                a,b=((1,),(2,)) if profile=="morrowind" else ((1,0),(2,0))
                tag=b"FNAM" if profile=="morrowind" else b"FULL"
                scalar=b"INTV" if profile=="morrowind" else b"DATA"
                self.assertEqual(s.typed_fields(a)[0]["value"],"Old")
                rev=s.revision
                with self.assertRaises(ValueError):
                    s.apply_typed(rev,[(a,tag,0,{"value":"Changed"}),(b,scalar,0,{"value":True})])
                self.assertEqual(s.data,data)
                # TES3 GMST lacks a registered persistent named identity and is
                # intentionally not exposed by the desktop transaction.
                edits=[(a,tag,0,{"value":"Longer name"})]
                if profile!="morrowind":
                    edits.append((b,scalar,0,{"value":42}))
                s.apply_typed(rev,edits)
                self.assertEqual(s.typed_fields(a)[0]["value"],"Longer name")
                self.assertIn((b"ZZZZ",b"opaque"),s.rows[a]["parts"])
                if profile!="morrowind":self.assertEqual(s.typed_fields(b)[0]["value"],42)
                with self.assertRaises(ValueError):s.apply_typed(rev,edits)
                self.assertEqual(s.node((0,)).header,parse(profile,data)[0].header)

    def test_localized_deleted_and_experimental_guards(self):
        from chimster.native_editor import NativeSession
        for profile,localized,deleted in (("skyrim-se",True,False),("new-vegas",False,True),("skyrim-vr",False,False)):
            data,slots=self.fixture(profile,localized,deleted)
            s=NativeSession(profile,data,slots)
            with self.assertRaises(ValueError):
                s.apply_typed(s.revision,[((1,0),b"FULL",0,{"value":"Changed"})])
            self.assertEqual(s.data,data)

    def test_morrowind_setting_adapter(self):
        from chimster.native_typed_edit import edit
        from hashlib import sha256
        data,_=self.fixture("morrowind")
        updated=edit("morrowind",data,(2,),b"INTV",0,{"value":12},sha256(data).hexdigest())
        self.assertEqual(dict(subrecords("morrowind",parse("morrowind",updated)[2]))[b"INTV"],struct.pack("<i",12))
