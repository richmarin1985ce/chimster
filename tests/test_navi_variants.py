import unittest,struct
from chimster.fnv_navi_variants import ordinary,decode,infer_grid_order,split_neighbors

class TestVariants(unittest.TestCase):
    def test_exterior(self):
        raw=ordinary(0x800,0x801,[(1,2,3),(3,4,5)],grid=(-7,12),grid_order='yx',preferred_value=25)
        self.assertEqual(struct.unpack_from('<hh',raw,12),(12,-7))
        self.assertEqual(decode(raw,grid_order='yx')['grid'],(-7,12))
        self.assertEqual(decode(raw,grid_order='yx')['approximate_position'],(2,3,4))
        self.assertEqual(infer_grid_order([(raw,(-7,12))]),'yx')
    def test_ambiguous_and_conflict(self):
        a=ordinary(1,2,[(0,0,0)],grid=(3,3),grid_order='xy')
        b=ordinary(1,2,[(0,0,0)],grid=(3,4),grid_order='xy')
        with self.assertRaises(ValueError):infer_grid_order([(a,(3,3))])
        with self.assertRaises(ValueError):infer_grid_order([(b,(3,4)),(b,(4,3))])
    def test_island(self):
        raw=struct.pack('<IIIhh3f6fHH',32,1,2,0,0,0,0,0,0,0,0,2,2,0,3,1)+struct.pack('<9f3Hf',0,0,0,2,0,0,0,2,0,0,1,2,0)
        self.assertEqual(decode(raw,grid_order='xy')['triangles'],[(0,1,2)])
        with self.assertRaises(ValueError):decode(raw[:-1],grid_order='xy')
        with self.assertRaises(ValueError):decode(raw[:-6]+struct.pack('<Hf',3,0),grid_order='xy')
    def test_preferred(self):
        self.assertEqual(split_neighbors([1,2,3,3],[2]),([1,3],[2]))
        with self.assertRaises(ValueError):split_neighbors([1,2],[3])
    def test_invalid(self):
        with self.assertRaises(ValueError):ordinary(1,2,[(0,0,0)],grid=(0,32768),grid_order='xy')
        with self.assertRaises(ValueError):ordinary(1,2,[(0,0,float('nan'))],grid_order='xy')
