import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from chimster.project import Project
from chimster.editor_presence import Presence, discover, select, TTL
from chimster.mcp_bridge import Bridge
from chimster.mcp_operations import read_text

class EditPresenceTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.p=Project.create(self.root/"project","Demo","newvegas")
        p=self.root/"draft.json"
        p.write_text('{"old":1}',encoding="utf-8")
        self.p.add("draft","quest",p,0)

    def test_presence(self):
        d=self.root/"runtime"
        presence=Presence(d)
        presence.publish(self.p,"draft")
        rows=discover(d)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["selected"],"draft")
        self.assertEqual(select(presence.id,d).root,self.p.root)
        with patch("chimster.editor_presence.time.time",return_value=time.time()+TTL+2):
            self.assertEqual(discover(d),[])
        presence.close()
        self.assertEqual(discover(d),[])

    def test_edit_recovery(self):
        readonly=Bridge(self.p)
        sha=self.p.read()["artifacts"]["draft"]["sha256"]
        self.assertIsNone(readonly.creation.preview_replace("draft",'{"new":2}',1,sha)["proposal_token"])
        self.assertNotIn("project_apply_replace",readonly.registry)
        b=Bridge(self.p,False,True)
        with self.assertRaises(ValueError):
            b.creation.preview_replace("draft","not json",1,sha)
        q=b.creation.preview_replace("draft",'{"new":2}',1,sha)
        self.assertIn("-{",q["diff"])
        self.assertEqual(self.p.read()["revision"],1)
        with self.assertRaises(ValueError):
            b.apply_proposal(q["proposal_token"],False)
        r=b.apply_proposal(q["proposal_token"],True)
        self.assertEqual(r["revision"],2)
        self.assertEqual(read_text(self.p,"draft")["text"],'{"new":2}')
        with self.assertRaises(ValueError):
            b.apply_proposal(q["proposal_token"],True)
        undo=b.creation.recover("undo",2)
        self.assertEqual(read_text(self.p,"draft")["text"],'{"old":1}')
        redo=b.creation.recover("redo",undo["revision"])
        self.assertEqual(read_text(self.p,"draft")["text"],'{"new":2}')
        p=self.root/"other.txt"
        p.write_text("other")
        self.p.add("other","other",p,redo["revision"])
        with self.assertRaises(ValueError):
            b.creation.recover("undo",redo["revision"])
        self.assertIn("other",self.p.read()["artifacts"])

if __name__=="__main__":
    unittest.main()
