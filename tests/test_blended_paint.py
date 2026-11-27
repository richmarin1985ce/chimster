import unittest
from chimster.land_paint import Paint
from chimster.blended_paint import stroke,remove_layer,usage
class BlendedTests(unittest.TestCase):
    def test_boundary_budget(self):
        p=Paint((("Dirt","Dirt"),("Dirt","Dirt")))
        layers=stroke(p,[],16,8,4,1,"Stone")
        self.assertEqual(len(layers),2)
        left,right=layers
        self.assertEqual(dict(left["vertices"])[8*17+16],dict(right["vertices"])[8*17])
        for t in ("A","B","C"):layers=stroke(p,layers,16,8,4,1,t)
        with self.assertRaises(ValueError):stroke(p,layers,16,8,4,1,"D")
        self.assertEqual(len(layers),8)
        erased=stroke(p,layers,16,8,4,1,"Stone",True)
        self.assertEqual(len(erased),8)
        reduced=remove_layer(erased,1,[0,0],0,"Stone")
        self.assertEqual(len(reduced),7);self.assertEqual(usage(reduced,1)[0]["writer_remaining"],1)
