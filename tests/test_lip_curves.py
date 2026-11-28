import struct
import unittest
from chimster import lip_curves as lc
from chimster import _openfacefx_lip_codec as codec

def fixture(game="Skyrim"):
    stride,targets,ticks=(33,16,132) if game=="Skyrim" else (60,43,240)
    head=struct.pack("<IIIHHiHH",1,ticks*2+28,1,2,3,-2,targets,3)
    cells=[{"frame":0,"curve":0,"value":.25},{"frame":1,"curve":0,"value":.75}]
    return head+codec.encode_curves(cells,stride,total_slots=2*stride)

class LipCurveTests(unittest.TestCase):
    def test_inspection(self):
        for game in ("Skyrim","Fallout4"):
            data=fixture(game)
            report=lc.inspect(data)
            self.assertTrue(report["byte_exact"])
            self.assertEqual(report["header"]["game"],game)
            self.assertEqual(report["slots"][0]["keys"],2)
            self.assertIn("1,0,0.75",lc.export_csv(data))
            with self.assertRaises(ValueError):lc.decode(data+b"x")

    def test_edit(self):
        data=fixture()
        changes=[{"frame":1,"slot":0,"value":.5}]
        with self.assertRaises(ValueError):lc.edit(data,changes)
        edited=lc.edit(data,changes,experimental=True)
        self.assertEqual(lc.decode(edited)[1][1]["value"],.5)
        self.assertEqual(edited[:24],data[:24])
        with self.assertRaises(ValueError):lc.edit(fixture("Fallout4"),changes,experimental=True)
        with self.assertRaises(ValueError):lc.edit(data,[{"frame":1,"slot":1,"value":.5}],experimental=True)
        with self.assertRaises(ValueError):lc.edit(data,[{"frame":1,"slot":0,"value":float("nan")}],experimental=True)
