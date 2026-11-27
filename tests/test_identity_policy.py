import unittest
import struct
from chimster.formids import FormIDs
from chimster.identity_policy import policy, header_cursor, reserve_hierarchy

class IdentityPolicyTests(unittest.TestCase):
    def test_hierarchy_and_cursor(self):
        ids=FormIDs("test.esp")
        parents={"z":None,"a":"z","b":"z","aa":"a"}
        result=reserve_hierarchy(ids,parents,cursor=0x900,occupied=[0x901])
        self.assertEqual(list(result),["z","a","b","aa"])
        self.assertEqual(result["z"],0x902)
        self.assertEqual(reserve_hierarchy(ids,parents),result)
    def test_cycles_and_exhaustion_are_atomic(self):
        ids=FormIDs("test.esp")
        before=ids.snapshot()
        for parents,cursor in [({"a":"b","b":"a"},0),({"a":None,"b":None},0xfff)]:
            with self.assertRaises(ValueError):
                reserve_hierarchy(ids,parents,policy("light"),cursor)
            self.assertEqual(ids.snapshot(),before)
    def test_policy_and_header(self):
        self.assertEqual(policy("medium").maximum,0xffff)
        self.assertEqual(policy("light",True).minimum,1)
        self.assertEqual(header_cursor(struct.pack("<fII",1.0,4,0x1000900)),0x900)
