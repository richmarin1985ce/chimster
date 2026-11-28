import struct,unittest
from types import SimpleNamespace
from chimster.native_render_records import decode,report,select_lights,water_data
from chimster.record_graph import Slots,Identity

class NativeRenderTests(unittest.TestCase):
    def test_native_records(self):
        slots=Slots("test.esp",[])
        raw=struct.pack("<iI4BIffIf",0,1280,255,128,0,0,0x600,1.,60.,0,0.)
        row=decode("LIGH",[(b"DATA",raw),(b"FMAM",struct.pack("<f",2.))],slots)
        self.assertEqual(row["native_light"]["radius"],1280)
        self.assertEqual(row["native_light"]["flags"],0x600)
        self.assertEqual(row["native_light"]["color"][0],1.)
        visual=bytearray(196)
        struct.pack_into("<f",visual,20,.5);visual[40:44]=bytes((10,20,30,0));visual[44:48]=bytes((5,10,15,0))
        struct.pack_into("<3f",visual,140,1.,0.,1280.)
        wat=decode("WATR",[(b"DNAM",bytes(visual)),(b"ANAM",b"\x80"),(b"FNAM",b"\x02")],slots)
        self.assertEqual(wat["native_water"]["deep"],(5/255,10/255,15/255))
        light=bytes((64,64,64,0,255,255,255,0,30,40,50,0))+struct.pack("<2f2i3f",0.,1280.,0,0,1.,2000.,1.)
        cell=decode("CELL",[(b"DATA",b"\x03"),(b"XCLL",light),(b"XCLW",struct.pack("<f",256.)),(b"XCWT",struct.pack("<I",0x802))],slots)
        key=Identity("test.esp",0x801);waterkey=Identity("test.esp",0x802)
        browser=SimpleNamespace(profile="new-vegas",active={key:row,waterkey:wat})
        ref=dict(base=key,position=(128.,256.,384.),rotation=(0.,0.,0.))
        r=report(browser,cell,[ref],(0,0,0),128.,{})
        self.assertEqual(r["water_level"],2.)
        self.assertEqual(r["effects"]["water_reflectivity"],.5)
        lights=select_lights(r["lights"],(1,2,3))
        self.assertEqual(lights[0].position,(1.,2.,3.))
        self.assertEqual(lights[0].radius,10.)
        self.assertTrue(lights[0].shadows)
        self.assertEqual(len(select_lights(r["lights"]*6,(0,0,0))),4)
        self.assertEqual(sum(l.shadows for l in select_lights(r["lights"]*6,(0,0,0))),1)
        self.assertEqual(water_data([(b"DNAM",b"short")]),{})

    def test_fallout3_fade_and_world_inheritance(self):
        from chimster.native_render_records import fo3_world_values
        slots=Slots("fo3.esp",[])
        raw=struct.pack("<iI4BIffIf",0,256,255,255,255,0,0,1.,45.,0,0.)
        result=decode("LIGH",[(b"DATA",raw),(b"FNAM",struct.pack("<f",3.))],slots,"fallout3")
        self.assertEqual(result["native_light"]["fade"],3.)
        parent=Identity("fo3.esp",0x800);child=Identity("fo3.esp",0x801)
        root=decode("WRLD",[(b"DNAM",struct.pack("<2f",0.,512.)),(b"NAM2",struct.pack("<I",0x802))],slots,"fallout3")
        inherited=decode("WRLD",[(b"WNAM",struct.pack("<I",0x800)),(b"PNAM",b"\x09\x00")],slots,"fallout3")
        browser=SimpleNamespace(profile="fallout3",active={parent:root,child:inherited})
        self.assertEqual(fo3_world_values(browser,child),{"heights":(0.,512.),"water":("fo3.esp",0x802)})
        self.assertEqual(decode("LIGH",[(b"DATA",raw)],slots,"skyrim"),{})
