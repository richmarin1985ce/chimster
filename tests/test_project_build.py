import unittest,json
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.project import Project
from chimster.project_build import build
class ProjectBuildTests(unittest.TestCase):
    def test_revision(self):
        with TemporaryDirectory() as d:
            p=Project.create(Path(d)/"project","Test","newvegas");q=Path(d)/"records.json"
            spec={"schema":1,"records":[{"type":"GLOB","id":"One","fields":{"kind":"f","value":1}}]}
            q.write_text(json.dumps(spec));p.add("records","records",q,0)
            a=build(p,"records","records","gameplay","Gameplay.esp",1)
            spec["records"].insert(0,{"type":"GLOB","id":"Two","fields":{"kind":"f","value":2}})
            q.write_text(json.dumps(spec));p.add("records","records",q,2,True)
            b=build(p,"records","records","gameplay","Gameplay.esp",3)
            self.assertEqual(a["build"]["records"]["one"],b["build"]["records"]["one"])
            self.assertEqual(p.read()["revision"],4)
            self.assertTrue(p.verify()["valid"])
