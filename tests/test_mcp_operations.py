import tempfile
import unittest
from pathlib import Path
from chimster.project import Project
from chimster.mcp_bridge import Bridge
from chimster.mcp_operations import CreationSession, diagnose, read_text

class OperationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.p = Project.create(self.root/"project", "Example", "newvegas")

    def preview(self, session, **kwargs):
        args = dict(id="new", kind="other", filename="sample.psc",
                    text="Scriptname Sample", revision=0)
        args.update(kwargs)
        return session.preview(**args)

    def test_read_only_default(self):
        b = Bridge(self.p)
        self.assertNotIn("project_apply_create", b.registry)
        self.assertIsNone(self.preview(b.creation)["proposal_token"])
        self.assertEqual(self.p.read()["revision"], 0)

    def test_create_and_rollback(self):
        b = Bridge(self.p, True)
        self.assertIn("project_apply_create", b.registry)
        proposal = self.preview(b.creation)
        self.assertEqual(self.p.read()["revision"], 0)
        with self.assertRaises(ValueError):
            b.creation.apply("wrong")
        r = b.creation.apply(proposal["proposal_token"])
        self.assertEqual(r["revision"], 1)
        self.assertEqual(read_text(self.p, "new")["text"], "Scriptname Sample")
        self.assertTrue(diagnose(self.p, "new", "papyrus")["result"]["valid"])
        with self.assertRaises(ValueError):
            b.creation.apply(proposal["proposal_token"])
        with self.assertRaises(ValueError):
            self.preview(b.creation, revision=1)
        self.p.rollback(r["undo_target_revision"], 1)
        self.assertEqual(self.p.read()["artifacts"], {})

    def test_scope_and_conflict(self):
        s = CreationSession(self.p, True)
        for name in ("../escape", "C:escape", "CON.txt", "x\\escape"):
            with self.assertRaises(ValueError):
                self.preview(s, filename=name)
        q = self.preview(s)
        other = self.root/"other.txt"
        other.write_text("test")
        self.p.add("other","other",other,0)
        with self.assertRaises(ValueError):
            s.apply(q["proposal_token"])
        self.assertNotIn("new",self.p.read()["artifacts"])
        with self.assertRaises(ValueError):
            read_text(self.p, "../other")

if __name__ == "__main__":
    unittest.main()
