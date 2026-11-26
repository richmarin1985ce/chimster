import unittest,struct
from chimster.texture_budget import audit,enforce_plan
class BudgetTests(unittest.TestCase):
    def parts(self,n):
        return [(b"BTXT",struct.pack("<IBBh",1,0,0,-1))]+[p for i in range(n-1) for p in ((b"ATXT",struct.pack("<IBBh",i+2,0,0,i)),(b"VTXT",struct.pack("<H2xf",0,0.)))]
    def test_limits(self):
        for game,limit in [("oblivion",9),("newvegas",7),("fallout3",7)]:
            self.assertTrue(audit(self.parts(limit),game)["valid"])
            r=audit(self.parts(limit+1),game);self.assertFalse(r["valid"])
            self.assertEqual(len(r["quadrants"][0]["zero_opacity_layers"]),limit)
            self.assertEqual(r["quadrants"][1]["allocated"],0)
        self.assertFalse(audit(self.parts(2),"oblivionremastered")["valid"])
    def test_plan(self):
        rows=[{"cell":[0,0],"quadrant":0} for _ in range(6)]
        self.assertEqual(enforce_plan("newvegas",rows)["quadrants"][0]["remaining"],0)
        with self.assertRaises(ValueError):enforce_plan("newvegas",rows+rows[:1])
    def test_bad_alpha(self):
        r=audit(self.parts(2)[:-1]+[(b"VTXT",struct.pack("<H2xf",289,1.))],"newvegas")
        self.assertFalse(r["valid"])

    def test_classic_layout(self):
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from chimster.texture_budget import scan_land
        from chimster.fnv_patch import sub
        def rec(sig,body,form=0):return struct.pack("<4sIIII",sig,len(body),0,form,0)+body
        with TemporaryDirectory() as d:
            p=Path(d)/"Test.esp"
            body=rec(b"LAND",b"".join(sub(k,v) for k,v in self.parts(10)),0x800)
            grp=struct.pack("<4sI4sII",b"GRUP",20+len(body),b"LAND",0,0)+body
            p.write_bytes(rec(b"TES4",b"")+grp)
            report=scan_land(p,"oblivion")
            self.assertEqual(report["land_records"],1)
            self.assertFalse(report["valid"])
