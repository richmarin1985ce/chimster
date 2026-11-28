import struct
import unittest
from unittest.mock import MagicMock
from chimster import dialogue_audio as da,voice_record as vr,audio

class DialogueAudioTests(unittest.TestCase):
    def test_responses(self):
        def line(n):return struct.pack("<Ii4xB3xIB3x",2,20,n,0,0)
        parts=[(b"TRDT",line(1)),(b"NAM1",b"Hello\0"),(b"TRDT",line(2)),(b"NAM1",b"Goodbye\0")]
        self.assertEqual([(r["number"],r["text"]) for r in da.responses(parts)],[(1,"Hello"),(2,"Goodbye")])
        with self.assertRaises(ValueError):da.responses(parts+parts)
        with self.assertRaises(ValueError):da.responses(parts[:1])
        with self.assertRaises(ValueError):da.responses(parts[1:2])

    def test_mapping(self):
        r={"lines":[{"line_id":"test.esp:000800:1","text":"Hello"}],"errors":[]}
        m={"test.esp:000800:1":["Test.esp/Voice/Line"]}
        self.assertEqual(da.attach_paths(r,m)["lines"][0]["stem"],"Test.esp/Voice/Line")
        self.assertEqual(da.attach_paths(r,{})["unmapped"],list(m))
        with self.assertRaises(ValueError):da.attach_paths(r,{"unknown":[]})

    def test_record(self):
        sd=MagicMock()
        stream=sd.RawInputStream.return_value.__enter__.return_value
        stream.read.side_effect=lambda n:(b"\0"*(n*2),False)
        out=vr.record(.1,0,sd=sd)
        self.assertEqual(audio.wav_info(out)["frames"],1600)
        with self.assertRaises(ValueError):vr.record(.1,0,sd=sd,cancelled=lambda:True)
        stream.read.side_effect=lambda n:(b"\0"*(n*2),True)
        with self.assertRaises(ValueError):vr.record(.1,0,sd=sd)
