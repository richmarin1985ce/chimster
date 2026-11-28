import unittest
from copy import deepcopy
from chimster.interior_edit import History,make_portal
from chimster.interior_diagnostics import audit
from chimster.interior_activation import ActivationPreview
from chimster.interior_environment import sample
from chimster.interior_occlusion import audit as occlusion

class InteriorSystemsTests(unittest.TestCase):
    def fixture(self):
        layout={"schema":1,"rooms":[{"id":"A","min":[0,0,0],"max":[4,4,4]},
                    {"id":"B","min":[4,0,0],"max":[8,4,4]}],"portals":[],
                "triggers":[{"id":"T","room":"A","min":[1,1,1],"max":[2,2,2],"event":"arrival"}]}
        return {"schema":1,"cells":[{"id":"Cell","title":"Cell","layout":layout,"placements":[{"id":"Door","base":"DoorBase","position":[4,2,2]}]}]}

    def test_edit_connectivity_and_rollback(self):
        h=History(self.fixture())
        self.assertEqual(audit(h.current)["unreachable"],[("Cell","B")])
        portal=make_portal(h.current["cells"][0]["layout"],"P","A","B")
        h.edit("Cell","portal",portal);h.bind("Cell","P","Door")
        self.assertEqual(audit(h.current)["unreachable"],[])
        self.assertEqual(audit(h.current,closed=[("Cell","P")])["unreachable"],[("Cell","B")])
        before=deepcopy(h.current)
        with self.assertRaises(ValueError):h.edit("Cell","placement",{"id":"Door","base":"DoorBase","position":[0,0,0]})
        self.assertEqual(h.current,before)
        h.undo();self.assertNotIn("portal_doors",h.current["cells"][0])
        h.redo();self.assertEqual(h.current,before)

    def test_activation_budget_and_portal_state(self):
        layout=self.fixture()["cells"][0]["layout"]
        chains=[{"event":"arrival:enter","actions":[{"op":"emit","target":"close"}]},
                {"event":"close","actions":[{"op":"door","target":"Door","open":False}]}]
        preview=ActivationPreview(layout,chains,["Door"])
        with self.assertRaises(ValueError):preview.update([1.5,1.5,1.5],budget=1)
        self.assertTrue(preview.doors["Door"]);self.assertEqual(preview.triggers.inside,set())
        preview.update([1.5,1.5,1.5])
        self.assertEqual(preview.closed_portals({"P":"Door"}),["P"])
        with self.assertRaisesRegex(ValueError,"cyclic"):ActivationPreview(layout,[{"event":"a","actions":[{"op":"emit","target":"a"}]}],[])

    def test_environment_and_visibility(self):
        layout=self.fixture()["cells"][0]["layout"]
        layout["portals"]=[make_portal(layout,"P","A","B",inset=0)]
        env={"rooms":{"A":{"ambient":[.1,.1,.1]},"B":{"absorption":.2}},
             "lights":[{"id":"Lamp","room":"A","position":[2,2,2],"color":[1,0,0],"radius":3,"intensity":.5}]}
        preview=sample(layout,env,"A",[2,2,2])
        self.assertAlmostEqual(preview["rgb"][0],.6)
        self.assertAlmostEqual(preview["acoustic_gain"]["B"],.4)
        self.assertNotIn("B",sample(layout,env,"A",[2,2,2],closed=["P"])["acoustic_gain"])
        result=occlusion(layout,{"multibounds":[{"id":"M","room":"A","min":[0,0,0],"max":[3,3,3]}],
            "occluders":[{"id":"O","room":"A","corners":[[4,1,1],[4,3,1],[4,3,3],[4,1,3]]}]},
            [{"id":"Box","min":[1,1,1],"max":[2,2,2]}])
        self.assertEqual(result["assignments"],{"Box":"M"})
        self.assertEqual(result["issues"][0]["code"],"occluder-overlaps-portal")
