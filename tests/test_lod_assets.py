import unittest,struct
from chimster.lod_assets import dds_rgba,object_atlas,simplify
from chimster.atlas import Tile
from chimster.flora import Mesh,Recipe,generate
class AssetLodTests(unittest.TestCase):
    def test_dds(self):
        d=dds_rgba(1,1,bytes([1,2,3,4]))
        self.assertEqual(len(d),132);self.assertEqual(d[:4],b"DDS ")
        self.assertEqual(struct.unpack_from("<I",d,4)[0],124)
        self.assertEqual(d[128:],bytes([3,2,1,4]))
    def test_object_atlas(self):
        m=Mesh([(0,0,0),(1,0,0),(0,0,1)],[(0,0),(1,0),(0,1)],[((0,1,2),"a"),((0,2,1),"b")])
        t=[Tile(x,1,1,b"\xff\xff\xff\xff") for x in ("a","b")]
        c={x:{"tiling":False,"shader":"opaque"} for x in ("a","b")}
        out,rgba,layout=object_atlas(m,t,8,8,1,compatibility=c)
        self.assertEqual(len(out.vertices),6)
        self.assertEqual(len(layout),2)
        with self.assertRaises(ValueError):object_atlas(m,t,8,8,1,compatibility={"a":c["a"],"b":{"tiling":True}})
    def test_simplify(self):
        m=generate(Recipe(),2);s=simplify(m,.1)
        self.assertLessEqual(len(s.faces),len(m.faces))
