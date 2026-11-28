import struct, unittest
from chimster.fnv_navi_ownership import registration

class Ownership(unittest.TestCase):
    def setUp(self):
        self.cid=0x1000800; self.wid=0x1000801
        self.groups={1:{'type':1,'label':struct.pack('<I',self.wid).hex()},2:{'type':4,'label':struct.pack('<hh',-1,0).hex()},3:{'type':5,'label':struct.pack('<hh',-1,0).hex()},4:{'type':6,'label':struct.pack('<I',self.cid).hex()},5:{'type':9,'label':struct.pack('<I',self.cid).hex()}}
        self.cell={'signature':'CELL','flags':0,'groups':[1,2,3]}
        self.mesh={'signature':'NAVM','flags':0,'groups':[1,2,3,4,5]}
        self.records={self.cid:self.cell,self.wid:{'signature':'WRLD','flags':0,'groups':[]}}
        self.report={'raw_cell':self.cid,'vertices':[(4096,-8192,0),(5000,-8000,1),(8192,-4096,0)]}
        self.fields={b'DATA':b'\0',b'XCLC':struct.pack('<ii',1,-2)}
    def call(self):return registration(self.mesh,self.cell,self.report,self.fields,self.groups,self.records)
    def test_exterior(self):self.assertEqual(self.call(),{'world':self.wid,'grid':[1,-2]})
    def test_wrong_world(self):
        self.records[self.wid]['signature']='CELL'
        with self.assertRaisesRegex(ValueError,'parent WRLD'):self.call()
    def test_wrong_block(self):
        self.groups[3]['label']=struct.pack('<hh',0,0).hex()
        with self.assertRaisesRegex(ValueError,'sub-block'):self.call()
    def test_wrong_owner(self):
        self.groups[5]['label']=struct.pack('<I',self.wid).hex()
        with self.assertRaisesRegex(ValueError,'group owner'):self.call()
    def test_outside(self):
        self.report['vertices'][0]=(0,0,0)
        with self.assertRaisesRegex(ValueError,'outside'):self.call()
    def test_interior(self):
        self.cell['groups']=[];self.mesh['groups']=[4,5];self.fields={b'DATA':b'\1'}
        self.assertEqual(self.call(),{})
    def test_persistent(self):
        self.cell['flags']=0x400
        with self.assertRaisesRegex(ValueError,'nonpersistent'):self.call()

if __name__=='__main__':unittest.main()
