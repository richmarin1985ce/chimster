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

    def test_effects_ammunition_and_reputation(self):
        from chimster.fnv_patch import sub,record
        from chimster.fnv_world import group
        from chimster.fnv_quest import conditions
        from chimster.fnv_bindings import Bindings
        with TemporaryDirectory() as d:
            a=Path(d)/"Source.esp"
            a.write_bytes(record(b"TES4",sub(b"HEDR",struct.pack("<fII",1.34,4,0x802)))+group(0,b"MGEF",record(b"MGEF",sub(b"EDID",b"Effect\0"),0x800))+group(0,b"PROJ",record(b"PROJ",sub(b"EDID",b"Projectile\0"),0x801)))
            effect={"ref":{"plugin":a.name,"id":0x800},"magnitude":1,"area":0,"duration":1,"range":0,"actor_value":16}
            def row(id,type,fields):return {"id":id,"type":type,"fields":fields}
            common={"title":"Supply","model":"supply.nif","bounds":[0,0,0,1,1,1],"value":1,"weight":0.5}
            spec={"schema":1,"records":[row("Ability","SPEL",{"title":"Ability","type":4,"effects":[effect]}),row("Perk","PERK",{"title":"Perk","description":"Test","minimum_level":1,"ranks":1,"effects":[{"kind":"ability","rank":0,"priority":0,"ref":"Ability"}]}),row("Food","ALCH",{**common,"equipment_type":12,"food":True,"effects":[effect]}),row("Ammo","AMMO",{**common,"speed":1,"clip_rounds":1,"projectile":{"plugin":a.name,"id":0x801}}),row("Voice","VTYP",{"female":True}),row("Class","CLAS",{"title":"Trader","description":"Trader","tag_skills":[32,37,43,-1],"special":[5]*7,"services":["food","miscellaneous"]}),row("Rep","REPU",{"title":"Rep","value":100})]}
            p=Path(d)/"Gameplay.esp";result=export(spec,p,[a]);self.assertEqual(len(scan(p)["records"]),7)
            b=Bindings([a,p],Path(d)/"Quest.esp")
            value={"reputation":{"plugin":p.name,"id":result["records"]["rep"]&0xffffff},"axis":"fame","operator":"ge","value":.5}
            raw=list(subs(conditions([value],0x02000800,{0},b)))[0][1]
            self.assertEqual(struct.unpack("<B3xfIIIII",raw),(0x60,.5,574,result["records"]["rep"],1,0,0))
