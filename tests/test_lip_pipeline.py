import tempfile
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
from chimster import lip_pipeline as lp
from test_audio import wav

def lip():
    return struct.pack("<IIIHHiHH",1,132*30+28,13,30,3,-4,16,0)+b"test"

class LipPipelineTests(unittest.TestCase):
    def test_header(self):
        self.assertEqual(lp.header(lip())["payload_bytes"],4)
        self.assertEqual(lp.header(lip())["game"],"Skyrim")
        with self.assertRaises(ValueError):lp.header(lip(),"Fallout4")
        for data in (b"",b"not a lip",struct.pack("<IIIHHiHH",0,132*30+28,13,30,3,-4,16,0)+b"test"):
            with self.assertRaises(ValueError):lp.header(data)

    def test_receipt(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/"voice.wav";source.write_bytes(wav())
            tool=root/"tool";tool.write_bytes(b"fake executable")
            output=root/"output"
            def fake(args):Path(args[-1]).write_bytes(lip())
            with patch.object(lp.audio,"executable",return_value=str(tool)),patch.object(lp.audio,"run_tool",side_effect=fake):
                with self.assertRaises(ValueError):lp.build(source,output,game="Skyrim",transcript="Hi",tool=str(tool),backend="openfacefx")
                with self.assertRaises(ValueError):lp.build(source,output,game="Fallout4",transcript="Hi",tool=str(tool),backend="openfacefx",experimental=True)
                report=lp.build(source,output,game="Skyrim",transcript="Hi",tool=str(tool),backend="openfacefx",experimental=True)
            self.assertTrue(report["experimental"])
            self.assertFalse(report["runtime_verified"])
            self.assertTrue(lp.verify(output,source,"Hi")["audio_matches"])
            self.assertFalse(lp.verify(output,source,"Changed")["transcript_matches"])
