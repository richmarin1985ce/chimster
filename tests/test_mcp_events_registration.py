import json
import tempfile
import unittest
from pathlib import Path
from chimster.project import Project
from chimster.mcp_bridge import Bridge
from chimster.mcp_registration import register_config

class EventsRegistrationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.project=Project.create(self.root/"project","Demo","newvegas")
        self.bridge=Bridge(self.project)
        self.addCleanup(self.bridge.jobs.close)
        self.request("initialize",{"protocolVersion":"2025-11-25"})
        self.bridge.dispatch({"jsonrpc":"2.0","method":"notifications/initialized"})
    def request(self,method,params=None):
        return self.bridge.dispatch({"jsonrpc":"2.0","id":1,"method":method,"params":params or {}})
    def test_subscription(self):
        uri="chimster://project/status"
        self.assertIn("result",self.request("resources/subscribe",{"uri":uri}))
        self.assertEqual(self.bridge.subscriptions.poll(),[])
        p=self.root/"data.txt"
        p.write_text("sample")
        self.project.add("a","other",p,0)
        event=self.bridge.subscriptions.poll()
        self.assertEqual(event,[{"jsonrpc":"2.0","method":"notifications/resources/updated","params":{"uri":uri}}])
        self.assertEqual(self.bridge.subscriptions.poll(),[])
        self.request("resources/unsubscribe",{"uri":uri})
        self.project.remove("a",1)
        self.assertEqual(self.bridge.subscriptions.poll(),[])
        self.assertIn("error",self.request("resources/subscribe",{"uri":"file:///etc/passwd"}))
    def test_register_preserves_config(self):
        p=self.root/"client.json"
        old={"otherSetting":True,"mcpServers":{"existing":{"command":"other"}}}
        p.write_text(json.dumps(old))
        config={"mcpServers":{"chimster":{"command":"chimster","args":["--mcp"]}}}
        result=register_config(p,config)
        self.assertEqual(json.loads(Path(result["backup"]).read_text()),old)
        saved=json.loads(p.read_text())
        self.assertTrue(saved["otherSetting"])
        self.assertEqual(saved["mcpServers"]["existing"],old["mcpServers"]["existing"])
        self.assertEqual(saved["mcpServers"]["chimster"],config["mcpServers"]["chimster"])
        self.assertFalse(register_config(p,config)["changed"])
        with self.assertRaises(ValueError):
            register_config(p,{"mcpServers":{"chimster":{"command":"different"}}})
        self.assertEqual(json.loads(p.read_text()),saved)
    def test_create_config(self):
        p=self.root/"new.json"
        config={"mcpServers":{"chimster":{"command":"chimster","args":["--mcp"]}}}
        self.assertTrue(register_config(p,config)["changed"])
        self.assertEqual(json.loads(p.read_text()),config)

if __name__=="__main__":
    unittest.main()
