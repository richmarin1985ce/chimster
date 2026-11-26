import unittest,struct
from chimster.worldspace import Terrain
from chimster.world_tools import sample_height,brush,snap_placements
from chimster.land_layers import encode_layers
from chimster.fnv_records import subs
class WorldToolsTests(unittest.TestCase):
    def test_snap(self):
        t=Terrain(tuple(tuple(float(x+y) for x in range(33)) for y in range(33)),2,0)
        self.assertEqual(sample_height(t,3,5),4)
        self.assertEqual(snap_placements(t,[{"x_m":3,"y_m":5,"snap_to_ground":True,"height_offset_m":2}])[0]["z_m"],6)
        self.assertEqual(sample_height(t,64,64),64)
        with self.assertRaises(ValueError):sample_height(t,65,0)
    def test_brush(self):
        t=Terrain(tuple(tuple(8. if x==16 and y==16 else 0. for x in range(33)) for y in range(33)))
        s=brush(t,16,16,3,"smooth")
        self.assertAlmostEqual(s.heights[16][16],8/9)
        self.assertEqual(brush(t,16,16,3,"flatten",1,2).heights[16][16],2)
        self.assertEqual(t.heights[16][16],8)
    def test_layers(self):
        p={"cell":[0,0],"quadrant":1,"layer":0,"texture":"Dirt","vertices":[[288,1],[0,.5]]}
        raw=encode_layers([p],{"Dirt":0x800},1)[(0,0)]
        a,b=list(subs(raw))
        self.assertEqual(a,(b"ATXT",struct.pack("<IBBh",0x800,1,0,0)))
        self.assertEqual(struct.unpack("<H2xfH2xf",b[1]),(0,.5,288,1))
        with self.assertRaises(ValueError):encode_layers([p,p],{"Dirt":0x800},1)
