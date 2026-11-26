import unittest,struct
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.worldspace import Terrain
from chimster.fnv_world import build
from chimster.fnv_content import export_book
from chimster.fnv_records import scan,subs,HEADER
from chimster.books import Book
from chimster.land_paint import Paint
from chimster.collision import box,proxy,ray_box
from chimster.flora import Mesh
class WorldContentTests(unittest.TestCase):
    def test_placement_and_paint(self):
        t=Terrain(tuple(tuple(0. for _ in range(33)) for _ in range(33)),4,0)
        c={"statics":[{"id":"TestStatic","model":"chimster/test.nif","bounds":[-1,-1,-1,1,1,1]}],
           "placements":[{"base":"TestStatic","x_m":10,"y_m":20,"z_m":1,"yaw":90}],
           "textures":[{"id":"Dirt","diffuse":"chimster/dirt.dds","normal":"chimster/dirt_n.dds"}],
           "paint":[["Dirt","Dirt"],["Dirt","Dirt"]]}
        with TemporaryDirectory() as d:
            p=Path(d)/"World.esp";r=build(t,p,origin=(-1,-1),content=c)
            self.assertEqual(r["records"],{"WRLD":1,"CELL":2,"LAND":1,"STAT":1,"REFR":1,"TXST":1,"LTEX":1})
            recs=scan(p)["records"];ref=next(r for r in recs if r["signature"]=="REFR")
            with p.open("rb") as f:
                f.seek(ref["offset"]);_,size,*_=HEADER.unpack(f.read(24));fields=dict(subs(f.read(size)))
            self.assertAlmostEqual(struct.unpack("<6f",fields[b"DATA"])[0],-4096+320)
            c["placements"][0]["x_m"]=128
            with self.assertRaises(ValueError):build(t,Path(d)/"bad.esp",content=c)
    def test_paint(self):
        p=Paint((("a","a"),("a","a"))).validate(1)
        self.assertEqual(p.brush(0,0,.5,"b").quadrants(0,0),("b","a","a","a"))
    def test_books(self):
        with TemporaryDirectory() as d:
            for kind in ("book","note","journal"):
                p=Path(d)/(kind+".esp");b=Book("Test","Title",("First","Second"),"Writer",kind)
                self.assertEqual(export_book(b,p,"chimster/book.nif" if kind=="book" else None)["signature"],"BOOK" if kind=="book" else "NOTE")
    def test_collision(self):
        m=Mesh([(0,0,0),(2,0,0),(0,3,0),(0,0,4)],[(0,0)]*4,[((0,1,2),"a"),((0,2,3),"a")])
        lo,hi=box(m);self.assertEqual((lo,hi),((0,0,0),(2,3,4)))
        self.assertEqual(len(proxy(m).faces),12)
        self.assertEqual(ray_box((-1,1,1),(1,0,0),lo,hi),1)
        self.assertIsNone(ray_box((-1,5,1),(1,0,0),lo,hi))
