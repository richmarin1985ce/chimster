import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.dialogue_views import parse,inspect,remap,slot_mapping
FIXTURE='''<Diagram Version="12"><Nodes><Node Class="std:ShapeNode" Id="0"><Bounds>0,0,500,300</Bounds><ToolTip>02000801 </ToolTip><Text>Branch</Text></Node><Node Class="std:TableNode" Id="1"><Bounds>20,20,100,60</Bounds><ToolTip>02000802 - Custom</ToolTip><Caption>First</Caption></Node><Node Class="std:TableNode" Id="2"><Bounds>300,20,100,60</Bounds><ToolTip>02000803 - Custom</ToolTip></Node></Nodes><Links><Link Id="3"><Bounds>120,50,180,0</Bounds><Origin Id="1"/><Destination Id="2"/><Points><Point>120,50</Point><Point>300,50</Point></Points></Link></Links><Resources><Custom>Preserve</Custom></Resources></Diagram>'''
class ViewTests(unittest.TestCase):
    def test_roundtrip(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"02000800.xml";p.write_text(FIXTURE)
            q=Path(d)/"03000800.xml";m=slot_mapping(p,2,3)
            report=remap(p,q,m,positions={"2":[300,90]})
            self.assertEqual(report["nodes"],3)
            r=inspect(parse(q));self.assertEqual(r["record_form_ids"],["03000801","03000802","03000803"])
            self.assertEqual(r["links"][0]["points"],[[120,50],[300,120]])
            self.assertEqual(parse(q).findtext("./Resources/Custom"),"Preserve")
            self.assertEqual(p.read_text(),FIXTURE)
            with self.assertRaises(ValueError):remap(p,Path(d)/"04000800.xml",{"02000800":"04000800"})
    def test_security(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"02000800.xml";p.write_text('<!DOCTYPE Diagram [<!ENTITY test "x">]>'+FIXTURE)
            with self.assertRaises(ValueError):parse(p)
