import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from chimster.fragment_source import generate, export

class FragmentSourceTests(unittest.TestCase):
    def test_quest_wrapper(self):
        result=generate("skyrimse","QF_Demo","quest",[{"event":"stage 10","function":"Fragment_0","body":"SetStage(20)"}])
        self.assertIn("Extends Quest Hidden",result["source"])
        self.assertIn("Function Fragment_0()",result["source"])
        self.assertEqual(result["bindings"],[{"event":"stage 10","function":"Fragment_0"}])
    def test_dialogue_wrapper(self):
        result=generate("skyrim","TIF_Demo","dialogue",[{"event":"begin","function":"Fragment_0","body":""}])
        self.assertIn("Extends TopicInfo Hidden",result["source"])
        self.assertIn("ObjectReference akSpeakerRef",result["source"])
    def test_rejections(self):
        good={"event":"stage 10","function":"Fragment_0","body":""}
        for rows in ([good,good],[{**good,"body":"EndFunction"}],[{**good,"function":"Bad"}]):
            with self.assertRaises(ValueError):generate("skyrim","QF_Demo","quest",rows)
        with self.assertRaises(ValueError):generate("fallout4","QF_Demo","quest",[good])
    def test_export_no_overwrite(self):
        with TemporaryDirectory() as t:
            p=Path(t)/"QF_Demo.psc"
            rows=[{"event":"stage 10","function":"Fragment_0","body":""}]
            export("skyrim","QF_Demo","quest",rows,p)
            with self.assertRaises(FileExistsError):export("skyrim","QF_Demo","quest",rows,p)
