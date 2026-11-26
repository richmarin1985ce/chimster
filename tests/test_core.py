import tempfile, unittest, struct
from pathlib import Path
from chimster.core import inspect_plugin, plan, catalog, PROFILES

def rec(sig, payload=b'', hs=24): return sig+struct.pack('<I',len(payload))+b'\0'*(hs-8)+payload
def sub(sig,payload,hs): return sig+len(payload).to_bytes(hs-4,'little')+payload
class TestCore(unittest.TestCase):
 def scan(self, data, game):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'test.esp';p.write_bytes(data); before=p.read_bytes(); result=inspect_plugin(p,game);self.assertEqual(p.read_bytes(),before);return result
 def test_tes3(self):
  data=rec(b'TES3',sub(b'MAST',b'Morrowind.esm\0',8),16)+rec(b'CELL',b'',16)
  self.assertEqual(self.scan(data,'morrowind')['masters'],['Morrowind.esm'])
 def test_tes4_oblivion(self):
  data=rec(b'TES4',sub(b'MAST',b'Oblivion.esm\0',6),20)+rec(b'NPC_',b'',20)
  self.assertEqual(self.scan(data,'oblivion')['record_counts']['NPC_'],1)
 def test_group(self):
  inner=rec(b'CELL'); group=b'GRUP'+struct.pack('<I',24+len(inner))+bytes(16)+inner
  self.assertEqual(self.scan(rec(b'TES4')+group,'newvegas')['groups'],1)
 def test_truncated(self):
  with self.assertRaises(ValueError): self.scan(rec(b'TES4')+b'CELL','newvegas')
 def test_wrong_magic(self):
  with self.assertRaises(ValueError): self.scan(rec(b'TES3',hs=16),'newvegas')
 def test_bad_group(self):
  with self.assertRaises(ValueError): self.scan(rec(b'TES4')+b'GRUP'+struct.pack('<I',1000)+bytes(16),'newvegas')
 def test_plan(self):
  p=plan('newvegas','Make a town from a heightmap');self.assertEqual(len(p['workstreams']),2);self.assertFalse(p['writes_game_files'])
 def test_catalog(self):
  c=catalog();self.assertGreaterEqual(len(c),50);self.assertEqual(len({x['name'] for x in c}),len(c));self.assertTrue(all(g=='*' or g in PROFILES for x in c for g in x['games']))
if __name__=='__main__':unittest.main()
