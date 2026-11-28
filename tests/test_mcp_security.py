import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from chimster.project import Project,atomic_json
from chimster.mcp_bridge import Bridge
from chimster.mcp_security import load_request,review
from chimster.mcp_oauth import OAuthConfig,https_url

class SecurityTests(unittest.TestCase):
    def test_approval_and_audit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Project.create(Path(d)/"project","Demo","newvegas")
            b=Bridge(p,allow_create=True,allow_edit=True,require_approval=True)
            self.addCleanup(b.jobs.close)
            def call(name,**args):
                r=b.call({"name":name,"arguments":args})
                self.assertFalse(r.get("isError"),r)
                return json.loads(r["content"][0]["text"])
            q=call("project_preview_create",id="draft",kind="other",filename="draft.txt",text="private draft",revision=0)
            token=q["proposal_token"]
            request=call("project_apply_create",token=token)
            self.assertTrue(request["approval_required"])
            self.assertEqual(p.read()["revision"],0)
            key=request["request_id"]
            self.assertEqual(call("project_apply_create",token=token)["request_id"],key)
            with patch("sys.stdin.isatty",return_value=True),patch("sys.stdout.isatty",return_value=True),patch("builtins.input",return_value="APPROVE"),patch("builtins.print"):
                self.assertEqual(review(p,key)["decision"],"approved")
            after=call("project_apply_create",token=token)
            self.assertEqual(after["revision"],1)
            self.assertTrue(b.call({"name":"project_apply_create","arguments":{"token":token}})["isError"])
            events=[json.loads(x.read_text()) for x in (p.meta/"mcp-audit").glob("*.json")]
            self.assertIn("completed",{e["outcome"] for e in events})
            self.assertNotIn(token,json.dumps(events))
            self.assertNotIn("private draft",json.dumps(events))
            self.assertFalse((p.meta/"mcp-approvals"/(key+".json")).exists())
            undo=call("project_undo",revision=1)
            path,row=load_request(p,undo["request_id"])
            row["decision"]="denied";atomic_json(path,row)
            self.assertTrue(b.call({"name":"project_undo","arguments":{"revision":1}})["isError"])
            self.assertEqual(p.read()["revision"],1)

    def test_oauth_claims(self):
        c=OAuthConfig.__new__(OAuthConfig)
        c.resource="https://example.org/mcp"
        c.issuer="https://issuer.example.org"
        c.endpoint=c.issuer+"/introspect"
        c.client_id="id";c.client_secret="secret"
        c.opener=MagicMock()
        stream=c.opener.open.return_value.__enter__.return_value
        valid={"active":True,"iss":c.issuer,"aud":c.resource,"exp":time.time()+60,
               "sub":"user","scope":"chimster:read"}
        stream.read.return_value=json.dumps(valid).encode()
        self.assertTrue(c.authenticate("opaque-token"))
        for invalid in ({"active":False},{"aud":"other"},{"iss":"other"},{"exp":0},{"exp":float("inf")},{"scope":"other"},{"nbf":time.time()+60},{"sub":""}):
            stream.read.return_value=json.dumps({**valid,**invalid}).encode()
            self.assertIsNone(c.authenticate("opaque-token"),invalid)
        self.assertIsNone(c.authenticate("bad token"))
        with self.assertRaises(ValueError):https_url("http://example.org/mcp",True)
        with self.assertRaises(ValueError):https_url("https://example.org/mcp\n",True)

if __name__=="__main__":
    unittest.main()
