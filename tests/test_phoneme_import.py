import json
from pathlib import Path
import tempfile
import unittest
from chimster import phoneme_import as pi, morph_calibration as mc

class PhonemeTests(unittest.TestCase):
    def test_import(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"phones.csv"
            p.write_text("phoneme,start,end\nʃ,0,0.4\ncustom,0.4,1\n",encoding="utf-8")
            rows=pi.load(p,1)
            self.assertEqual([r["phoneme"] for r in rows],["ʃ","custom"])
            with self.assertRaises(ValueError):pi.load(p,.9)
    def test_grid(self):
        grid='''item [1]:
 class = "IntervalTier"
 name = "phones"
 intervals: size = 2
 intervals [1]:
  xmin = 0
  xmax = 0.5
  text = "AA1"
 intervals [2]:
  xmin = 0.5
  xmax = 1
  text = ""
'''
        self.assertEqual([r["phoneme"] for r in pi.validate(pi.textgrid(grid),1)],["AA1","sil"])
        with self.assertRaises(ValueError):pi.textgrid(grid,"words")
    def test_mapping(self):
        obs={str(s):{"observed":False,"morph":""} for s in range(33)}
        p={"schema":1,"game":"Skyrim","observations":obs,"phonemes":{"ʃ":{"22":.7}}}
        rows=[{"phoneme":"ʃ","start":0,"end":1}]
        with self.assertRaises(ValueError):mc.preview(rows,1,p)
        obs["22"]={"observed":True,"morph":"example observation"}
        self.assertEqual(mc.preview(rows,1,p)["segments"][0]["slots"],{"22":.7})
        with self.assertRaises(ValueError):mc.preview([{"phoneme":"unknown","start":0,"end":1}],1,p)
