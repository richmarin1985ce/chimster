import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave
from chimster import audio_edit as ae

def fixture(values=(1000,-1000,2000,-2000),rate=4):
    out=io.BytesIO()
    with wave.open(out,"wb") as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(rate)
        f.writeframes(struct.pack("<"+"h"*len(values),*values))
    return out.getvalue()

class AudioEditTests(unittest.TestCase):
    def test_selection_and_envelope(self):
        c=ae.Clip(fixture())
        self.assertEqual(c.duration,1)
        self.assertEqual(c.envelope(2),[(-1000/32768,1000/32768),(-2000/32768,2000/32768)])
        self.assertEqual(ae.Clip(c.edited(.25,.75)).data,struct.pack("<hh",-1000,2000))
        for a,b in ((0,0),(-1,1),(0,2),(float("nan"),1)):
            with self.assertRaises(ValueError):c.edited(a,b)

    def test_gain_and_fades(self):
        c=ae.Clip(fixture((20000,20000,-20000,-20000)))
        self.assertEqual(struct.unpack("<hhhh",ae.Clip(c.edited(gain_db=12)).data),(32767,32767,-32768,-32768))
        self.assertEqual(struct.unpack("<hhhh",ae.Clip(c.edited(fade_in=.25,fade_out=.25)).data),(0,20000,-20000,0))

    def test_cues(self):
        x={"mouthCues":[{"start":0,"end":.5,"value":"A"},{"start":.5,"end":1,"value":"X"}]}
        y=ae.trim_cues(x,.25,.75,1)
        self.assertEqual(y["mouthCues"],[{"start":0,"end":.25,"value":"A"},{"start":.25,"end":.5,"value":"X"}])
        self.assertEqual(ae.edit_cue(x,0,0,.5,"B",1)["mouthCues"][0]["value"],"B")
        self.assertEqual(x["mouthCues"][0]["value"],"A")
        with self.assertRaises(ValueError):ae.edit_cue(x,0,0,.75,"A",1)

    def test_export_and_playback(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/"a.wav";path.write_bytes(fixture())
            c=ae.Clip.open(path)
            with self.assertRaises(FileExistsError):c.export(path)
            with patch.object(ae.shutil,"which",return_value="ffplay"),patch.object(ae.subprocess,"Popen") as p:
                ae.play(path,.25,.75)
                self.assertEqual(p.call_args.args[0][-5:],["-ss","0.25","-t","0.5",str(path)])
