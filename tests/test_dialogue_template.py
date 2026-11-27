import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.dialogue_views import generate_from_template,parse

class TemplateTests(unittest.TestCase):
    def test_preserve_resources(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"02000800.xml";q=Path(d)/"03000800.xml"
            p.write_text('<Diagram Version="12"><Nodes><Node Id="1" Class="std:TableNode"><Bounds>0,0,100,60</Bounds><ToolTip>02000801 - Topic</ToolTip><CustomStyle>Keep</CustomStyle></Node></Nodes><Links/><Resources><Custom>Keep</Custom></Resources></Diagram>')
            graph={"nodes":[{"id":"1"}],"edges":[]}
            generate_from_template(p,q,graph,{"1":"03000801"})
            root=parse(q)
            self.assertEqual(root.findtext("./Resources/Custom"),"Keep")
            self.assertEqual(root.findtext("./Nodes/Node/CustomStyle"),"Keep")
            self.assertEqual(root.findtext("./Nodes/Node/ToolTip"),"03000801 - Topic")
            with self.assertRaises(ValueError):
                generate_from_template(p,Path(d)/"04000800.xml",{"nodes":[],"edges":[]},{})
