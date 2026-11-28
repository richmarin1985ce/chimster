import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from chimster.project import Project
from chimster.mcp_bridge import Bridge
from chimster.mcp_operations import revision_diff, inspect_record, check_world

def request(b, method, params=None):
    return b.dispatch({"jsonrpc":"2.0","id":1,"method":method,"params":params or {}})

class ResourceTests(unittest.TestCase):
    def setUp(self):
        d=tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root=Path(d.name)
        self.p=Project.create(self.root/"project","Demo","newvegas")
        self.b=Bridge(self.p)
        request(self.b,"initialize",{"protocolVersion":"2025-11-25"})
        self.b.dispatch({"jsonrpc":"2.0","method":"notifications/initialized"})

    def add(self,key,name,revision):
        p=self.root/name
        p.write_bytes(b"synthetic")
        self.p.add(key,"plugin",p,revision)

    def test_resource_scope(self):
        self.add("sample","Sample.esp",0)
        listed=request(self.b,"resources/list")["result"]["resources"]
        self.assertEqual(len(listed),3)
        self.assertIn('chimster://editor/context',{x['uri'] for x in listed})
        uri="chimster://project/artifacts/sample"
        data=request(self.b,"resources/read",{"uri":uri})["result"]["contents"][0]
        self.assertEqual(json.loads(data["text"])["artifact"]["filename"],"Sample.esp")
        for uri in ("file:///etc/passwd","chimster://project/artifacts/../sample"):
            self.assertIn("error",request(self.b,"resources/read",{"uri":uri}))
        self.assertEqual(Bridge().resource_templates(),[])

    def test_revision_diff(self):
        self.add("a","A.esp",0)
        self.add("b","B.esp",1)
        data=revision_diff(self.p,0,limit=1)
        self.assertEqual(data["total"],2)
        self.assertEqual(data["next_offset"],1)
        self.assertEqual(data["changes"][0]["change"],"added")
        self.p.remove("a",2)
        self.assertEqual(revision_diff(self.p,2)["changes"][0]["change"],"removed")

    def test_original_filename_and_order(self):
        self.add("master","Master.esm",0)
        self.add("mod","Mod.esp",1)
        with patch("chimster.record_editor.inspect") as inspect:
            inspect.side_effect=lambda p,origin,local: {"name":p.name}
            self.assertEqual(inspect_record(self.p,"mod","Mod.esp",1)["record"]["name"],"Mod.esp")
        with patch("chimster.world_validator.validate") as validate:
            validate.side_effect=lambda paths,**kw: {"names":[p.name for p in paths]}
            self.assertEqual(check_world(self.p,["master","mod"])["report"]["names"],["Master.esm","Mod.esp"])
        for args in ({"ids":["mod","mod"]},{"ids":["mod"],"navmesh":"yes"},{"ids":[1]}):
            response=request(self.b,"tools/call",{"name":"fnv_world_check","arguments":args})
            self.assertTrue("error" in response or response["result"].get("isError"))

if __name__=="__main__":
    unittest.main()
