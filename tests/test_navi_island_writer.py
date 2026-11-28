import unittest,struct
from chimster.fnv_navi_variants import island,decode

class TestIslandWriter(unittest.TestCase):
    vs=[(0.,0.,0.),(3.,0.,0.),(0.,3.,0.)]
    ts=[(0,1,2)]
    reference=struct.pack('<IIIhh3f6fHH',32,1,2,0,0,1,1,0,0,0,0,3,3,0,3,1)+struct.pack('<9f3Hf',0,0,0,3,0,0,0,3,0,0,1,2,0)
    def make(self,**kw):
        args=dict(reference=self.reference,reference_vertices=self.vs,reference_triangles=self.ts,grid_order='yx');args.update(kw)
        return island(10,20,self.vs,self.ts,**args)
    def test_new_identity(self):
        r=decode(self.make(grid=(-2,3)),grid_order='yx')
        self.assertEqual((r['mesh'],r['location'],r['grid']),(10,20,(-2,3)))
        self.assertEqual(r['triangles'],self.ts)
    def test_reference_mismatch(self):
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.make(reference_triangles=[(0,2,1)])
    def test_other_flags(self):
        with self.assertRaisesRegex(ValueError,'no other flags'):
            self.make(reference=struct.pack('<I',0x21)+self.reference[4:])
    def test_degenerate(self):
        with self.assertRaisesRegex(ValueError,'degenerate'):
            island(10,20,[(0,0,0),(1,1,0),(2,2,0)],self.ts,reference=self.reference,reference_vertices=self.vs,reference_triangles=self.ts,grid_order='yx')
