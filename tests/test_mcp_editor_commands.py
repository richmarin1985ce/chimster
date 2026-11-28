import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from chimster.project import Project
from chimster.editor_presence import Presence
from chimster.editor_commands import mailbox,submit,consume,TTL
from chimster.mcp_bridge import Bridge

class EditorCommandTests(unittest.TestCase):
    def test_scope_and_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=Project.create(root/"project","Demo","newvegas")
            other=Project.create(root/"other","Other","newvegas")
            src=root/"draft.txt"
            src.write_text("draft")
            p.add("draft","other",src,0)
            runtime=root/"runtime"
            presence=Presence(runtime)
            mailbox(presence.id,runtime,create=True)
            presence.publish(p)
            calls=[]
            callback=lambda action,artifact:calls.append((action,artifact))
            result=submit(p,presence.id,"select",1,"draft",runtime)
            self.assertEqual(result["state"],"queued")
            consume(p,presence.id,callback,runtime)
            self.assertEqual(calls,[("select","draft")])
            consume(p,presence.id,callback,runtime)
            self.assertEqual(len(calls),1)
            with self.assertRaises(ValueError):
                submit(other,presence.id,"refresh",0,root=runtime)
            with self.assertRaises(ValueError):
                submit(p,presence.id,"refresh",0,root=runtime)
            with self.assertRaises(ValueError):
                submit(p,presence.id,"shell",1,root=runtime)
            submit(p,presence.id,"refresh",1,root=runtime)
            with patch("chimster.editor_commands.time.time",return_value=time.time()+TTL+1):
                consume(p,presence.id,callback,runtime)
            self.assertEqual(len(calls),1)
            submit(p,presence.id,"viewport-fit",1,root=runtime)
            consume(p,presence.id,callback,runtime)
            self.assertEqual(calls[-1],("viewport-fit",None))
            with self.assertRaises(ValueError):
                submit(p,presence.id,"viewport-delete",1,root=runtime)
            self.assertNotIn("editor_request",Bridge(p).registry)
            self.assertIn("editor_request",Bridge(p,allow_ui=True).registry)
            self.assertEqual(p.read()["revision"],1)

if __name__=="__main__":
    unittest.main()
