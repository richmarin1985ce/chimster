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

    def test_group_layout(self):
        import struct
        from chimster.fnv_records import HEADER,subs
        with TemporaryDirectory() as d:
            p=Path(d)/"World.esp";build(self.terrain(),p,origin=(-1,-1))
            raw=p.read_bytes();locations={};persistent=[]
            def walk(start,end,parents=()):
                while start<end:
                    kind,size,*_=HEADER.unpack_from(raw,start)
                    if kind==b"GRUP":
                        _,_,label,typ,_,_=struct.unpack_from("<4sI4sIII",raw,start)
                        self.assertGreaterEqual(size,24)
                        self.assertLessEqual(start+size,end)
                        walk(start+24,start+size,parents+((typ,label),))
                        start+=size
                    else:
                        _,_,flags,form,*_=HEADER.unpack_from(raw,start)
                        fields=dict(subs(raw[start+24:start+24+size]))
                        if kind==b"CELL":
                            x,y,_=struct.unpack("<iiI",fields[b"XCLC"])
                            if flags&0x400:
                                self.assertEqual([g[0] for g in parents],[0,1]);persistent.append(form)
                            else:
                                self.assertEqual([g[0] for g in parents],[0,1,4,5])
                                self.assertEqual(struct.unpack("<hh",parents[-2][1]),(y//32,x//32))
                                self.assertEqual(struct.unpack("<hh",parents[-1][1]),(y//8,x//8))
                                locations[form]=(x,y)
                        if kind==b"LAND":
                            self.assertEqual([g[0] for g in parents],[0,1,4,5,6,9])
                            cid=struct.unpack("<I",parents[-1][1])[0]
                            self.assertIn(cid,locations)
                            self.assertEqual(parents[-1][1],parents[-2][1])
                        start+=size+24
                self.assertEqual(start,end)
            walk(0,len(raw))
            self.assertEqual(len(persistent),1)
            self.assertEqual(set(locations.values()),{(-1,-1),(-1,0),(0,-1),(0,0)})
