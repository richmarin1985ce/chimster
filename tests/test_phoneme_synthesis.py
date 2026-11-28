import unittest
from chimster import phoneme_synthesis as ps,lip_curves as lc
from chimster.morph_profile_ui import empty

class PhonemeSynthesisTests(unittest.TestCase):
    def test_synthesis(self):
        p=empty()
        p["observations"]["22"]={"observed":True,"morph":"test jaw"}
        p["phonemes"]["custom"]={"22":.8}
        rows=[{"phoneme":"custom","start":0,"end":1}]
        with self.assertRaises(ValueError):ps.synthesize(rows,1,p)
        blob=ps.synthesize(rows,1,p,experimental=True)
        meta,cells,_=lc.decode(blob)
        self.assertEqual(meta["game"],"Skyrim")
        self.assertEqual(meta["frames"],31)
        self.assertAlmostEqual(max(c["value"] for c in cells if c["curve"]==22),.8)
        self.assertTrue(lc.inspect(blob)["byte_exact"])
        with self.assertRaises(ValueError):ps.synthesize([{"phoneme":"unknown","start":0,"end":1}],1,p,experimental=True)
    def test_invalid_observation(self):
        p=empty();p["phonemes"]["a"]={"22":1}
        with self.assertRaises(ValueError):ps.frames([{"phoneme":"a","start":0,"end":1}],1,p)
