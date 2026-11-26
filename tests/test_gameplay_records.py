import unittest,struct
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.record_project import export,remove
from chimster.fnv_records import scan,subs,HEADER
class GameplayTests(unittest.TestCase):
    def project(self):
        def row(id,type,fields):return {"id":id,"type":type,"fields":fields}
        return {"schema":1,"records":[row("Rep","REPU",{"title":"Reputation","value":100}),row("Traders","FACT",{"title":"Traders","allow_sell":True,"reputation":"Rep","ranks":[{"rank":0,"male":"Trader","female":"Trader"}]}),row("Cargo","MISC",{"title":"Cargo","model":"cargo.nif","bounds":[0,0,0,1,1,1],"value":10,"weight":2}),row("Stock","LVLI",{"entries":[{"ref":"Cargo","level":1,"count":2}]}),row("Chest","CONT",{"title":"Stock","model":"chest.nif","bounds":[0,0,0,1,1,1],"items":[{"ref":"Stock","count":1}]}),row("Zone","ECZN",{"minimum_level":2,"owner":"Traders"})]}
    def test_native(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"Gameplay.esp";r=export(self.project(),p);ids=r["records"]
            recs=scan(p)["records"]
            self.assertEqual(len(recs),6)
            fields={}
            with p.open("rb") as f:
                for a in recs:
                    f.seek(a["offset"]);_,n,*_=HEADER.unpack(f.read(24));fields[a["editor_id"]]=dict(subs(f.read(n)))
            self.assertEqual(struct.unpack("<Ii",fields["Chest"][b"CNTO"]),(ids["stock"],1))
            self.assertEqual(struct.unpack("<I",fields["Traders"][b"WMI1"])[0],ids["rep"])
            self.assertEqual(struct.unpack("<h2xIh2x",fields["Stock"][b"LVLO"]),(1,ids["cargo"],2))
    def test_ref_guards(self):
        p=self.project()
        with self.assertRaises(ValueError):remove(p,"Cargo")
        p["records"][3]["fields"]["entries"][0]["ref"]="Stock"
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):export(p,Path(d)/"Bad.esp")
        p=self.project();p["records"][4]["fields"]["items"][0]["ref"]="Rep"
        with TemporaryDirectory() as d:
            with self.assertRaises(ValueError):export(p,Path(d)/"Bad.esp")
