import io,json,tempfile,unittest,wave
from pathlib import Path
from chimster.drop_import import classify,load_bundle

class DropImportTests(unittest.TestCase):
    def test_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);wav=p/"voice space.wav"
            with wave.open(str(wav),"wb") as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b"\0"*32000)
            timeline=p/"phonemes.csv";timeline.write_text("phoneme,start,end\ncustom,0,1\n")
            profile=p/"profile.json";profile.write_text(json.dumps({"schema":1,"game":"Skyrim","observations":{str(i):{"observed":False,"morph":""} for i in range(33)}}))
            current={"rows":[],"duration":None}
            state=load_bundle([profile,timeline,wav],current)
            self.assertEqual(state["duration"],1)
            self.assertEqual(state["rows"][0]["phoneme"],"custom")
            self.assertEqual(state["profile"]["game"],"Skyrim")
            self.assertIsNone(current["duration"])
            with self.assertRaises(ValueError):classify([wav,wav])
            with self.assertRaises(ValueError):load_bundle([timeline],current)
            timeline.write_text("phoneme,start,end\ncustom,0,2\n")
            with self.assertRaises(ValueError):load_bundle([wav,timeline],current)
            self.assertEqual(current["rows"],[])
