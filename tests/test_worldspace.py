import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.worldspace import Terrain,TerrainHistory
from chimster.fnv_world import encode_height,decode_height,build,normals
class WorldTests(unittest.TestCase):
    def terrain(self):
        return Terrain(tuple(tuple(2100+x*.4+y*.2 for x in range(65)) for y in range(65)),4,2100)
    def test_sculpt(self):
        t=self.terrain();h=TerrainHistory(t);h.sculpt(32,32,4,3)
        self.assertEqual(h.current.heights[32][32],t.heights[32][32]+3)
        self.assertEqual(tuple(r[-1] for r in h.current.cell(0,0)),tuple(r[0] for r in h.current.cell(1,0)))
        h.undo();self.assertEqual(h.current,t);h.redo();self.assertNotEqual(h.current,t)
    def test_codec(self):
        g=tuple(tuple(x-y*3 for x in range(33)) for y in range(33))
        self.assertEqual(decode_height(encode_height(g)),g)
        with self.assertRaises(ValueError):encode_height(tuple(tuple(x*128 for x in range(33)) for y in range(33)))
    def test_normals_seam(self):
        g=tuple(tuple(x-y for x in range(65)) for y in range(65))
        a,b=normals(g,0,0),normals(g,32,0)
        for y in range(33):self.assertEqual(a[(y*33+32)*3:(y*33+33)*3],b[y*99:y*99+3])
    def test_writer(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"World.esp";r=build(self.terrain(),p,origin=(-1,-1))
            self.assertEqual(r["records"],{"WRLD":1,"CELL":5,"LAND":4})
            self.assertLessEqual(r["max_quantization_error_game_units"],4.0001)
            with self.assertRaises(ValueError):build(self.terrain(),p)
