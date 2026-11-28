import io
import json
import tempfile
import unittest
from pathlib import Path
from chimster.project import Project
from chimster.mcp_bridge import Bridge, serve, MAX_LINE

def request(b, method, params=None):
    return b.dispatch({"jsonrpc":"2.0","id":1,"method":method,"params":params or {}})

def ready(b):
    request(b,"initialize",{"protocolVersion":"2025-11-25"})
    b.dispatch({"jsonrpc":"2.0","method":"notifications/initialized"})

class BridgeTests(unittest.TestCase):
    def test_lifecycle(self):
        b=Bridge()
        self.assertEqual(request(b,"tools/list")["error"]["code"],-32002)
        ready(b)
        self.assertEqual([t["name"] for t in request(b,"tools/list")["result"]["tools"]],["chimster_capabilities"])
        self.assertEqual(request(b,"shell/execute")["error"]["code"],-32601)

    def test_scoped_project(self):
        with tempfile.TemporaryDirectory() as d:
            p=Project.create(Path(d)/"project","Example","newvegas")
            src=Path(d)/"asset.txt"
            src.write_text("example")
            p.add("asset","other",src,0)
            b=Bridge(p)
            ready(b)
            def call(name,args=None):
                return request(b,"tools/call",{"name":name,"arguments":args or {}})
            def data(name,args=None):
                return json.loads(call(name,args)["result"]["content"][0]["text"])
            self.assertEqual(data("project_status")["revision"],1)
            self.assertEqual(data("project_artifacts",{"limit":1})["items"][0]["id"],"asset")
            self.assertTrue(data("project_verify")["valid"])
            self.assertEqual(call("project_status",{"path":"/etc/passwd"})["error"]["code"],-32602)
            self.assertEqual(call("project_artifacts",{"limit":True})["error"]["code"],-32602)
            self.assertEqual(call("project_artifacts",{"limit":101})["error"]["code"],-32602)
            self.assertTrue(call("project_artifact",{"id":"../private"})["result"]["isError"])
            self.assertEqual(call("project_remove",{"id":"asset"})["error"]["code"],-32602)
            self.assertEqual(p.read()["revision"],1)

    def test_stdio(self):
        sink=io.StringIO()
        serve(Bridge(),io.BytesIO(b'not json\n{"jsonrpc":"2.0","id":7,"method":"ping"}\n'),sink)
        replies=[json.loads(line) for line in sink.getvalue().splitlines()]
        self.assertEqual(replies[0]["error"]["code"],-32700)
        self.assertEqual(replies[1]["id"],7)
        sink=io.StringIO()
        serve(Bridge(),io.BytesIO(b"x"*(MAX_LINE+1)+b"\n"),sink)
        self.assertEqual(sink.getvalue(),"")

if __name__=="__main__":
    unittest.main()
