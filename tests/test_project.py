import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.project import Project
class ProjectTests(unittest.TestCase):
    def test_lifecycle(self):
        with TemporaryDirectory() as d:
            p=Project.create(Path(d)/"project","Example","newvegas")
            a=Path(d)/"quest.json";a.write_text("first")
            p.add("quest","quest",a,0)
            with self.assertRaises(ValueError):p.add("other","quest",a,0)
            a.write_text("second");p.add("quest","quest",a,1,True)
            self.assertEqual(p.object("quest").read_text(),"second")
            p.rollback(1,2);self.assertEqual(p.object("quest").read_text(),"first")
            self.assertEqual(p.read()["revision"],3)
            p.export("quest",Path(d)/"copy.json")
            self.assertTrue(p.verify()["valid"])
            p.object("quest").write_text("corrupt")
            self.assertFalse(p.verify()["valid"])
    def test_lock_and_duplicate(self):
        with TemporaryDirectory() as d:
            p=Project.create(Path(d)/"p","Test","skyrimse");a=Path(d)/"a";a.write_text("a")
            with p.lock():
                with self.assertRaises(ValueError):p.add("a","other",a,0)
            p.add("a","other",a,0)
            with self.assertRaises(ValueError):p.add("A","other",a,1)
            p.remove("a",1);self.assertEqual(p.read()["artifacts"],{})

    def test_batch_atomic_manifest(self):
        with TemporaryDirectory() as d:
            p=Project.create(Path(d)/"p","Test","newvegas");a=Path(d)/"a";a.write_text("a")
            first={"op":"add","id":"mesh","kind":"mesh","source":str(a)}
            with self.assertRaises(ValueError):p.batch([first,{"op":"remove","id":"missing"}],0)
            self.assertEqual(p.read()["revision"],0)
            self.assertEqual(p.read()["artifacts"],{})
            p.batch([first,{"op":"add","id":"texture","kind":"texture","source":str(a)}],0)
            self.assertEqual(p.read()["revision"],1)
            self.assertEqual(len(list((p.meta/"objects").iterdir())),1)
