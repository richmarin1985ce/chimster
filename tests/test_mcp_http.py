import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from chimster.project import Project
from chimster.mcp_http import Server,create_token,read_token

class HTTPTests(unittest.TestCase):
    def test_http(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            project=Project.create(root/"project","Example","newvegas")
            token=create_token(root/"token")
            self.assertEqual(read_token(root/"token"),token)
            with self.assertRaises(FileExistsError):
                create_token(root/"token")
            with Server(project,token) as server:
                t=threading.Thread(target=server.serve_forever,daemon=True)
                t.start()
                def send(method,msg=None,headers=None):
                    c=http.client.HTTPConnection("127.0.0.1",server.server_port,timeout=5)
                    try:
                        body=None if msg is None else json.dumps(msg)
                        h={"Content-Type":"application/json","Accept":"application/json, text/event-stream","Authorization":"Bearer "+token}
                        h.update(headers or {})
                        c.request(method,"/mcp",body=body,headers=h)
                        r=c.getresponse()
                        data=r.read()
                        return r.status,r.getheader("Mcp-Session-Id"),json.loads(data) if data else None
                    finally:c.close()
                try:
                    init={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}
                    self.assertEqual(send("POST",init,{"Authorization":"Bearer wrong"})[0],401)
                    self.assertEqual(send("POST",init,{"Host":"evil.example"})[0],403)
                    self.assertEqual(send("POST",init,{"Origin":"https://evil.example"})[0],403)
                    code,key,result=send("POST",init)
                    self.assertEqual(code,200)
                    self.assertTrue(key)
                    self.assertEqual(result["result"]["capabilities"]["resources"],{})
                    h={"Mcp-Session-Id":key,"MCP-Protocol-Version":"2025-11-25"}
                    self.assertEqual(send("POST",{"jsonrpc":"2.0","method":"notifications/initialized"},h)[0],202)
                    _,_,data=send("POST",{"jsonrpc":"2.0","id":2,"method":"tools/list"},h)
                    names={v["name"] for v in data["result"]["tools"]}
                    self.assertIn("project_status",names)
                    self.assertNotIn("project_apply_replace",names)
                    self.assertNotIn("fnv_record_apply_edit",names)
                    self.assertEqual(send("GET",headers=h)[0],405)
                    self.assertEqual(send("DELETE",headers=h)[0],204)
                    self.assertEqual(send("POST",{"jsonrpc":"2.0","id":3,"method":"ping"},h)[0],404)
                finally:
                    server.shutdown()
                    t.join(timeout=5)

if __name__=="__main__":
    unittest.main()
