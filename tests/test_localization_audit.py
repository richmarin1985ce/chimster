import unittest
from chimster.localization_audit import audit,audit_tables
class LocalizationAuditTests(unittest.TestCase):
    def test_tokens(self):
        self.assertTrue(audit("Hello {name}, %d","Hallo {name}, %d")["ok"])
        self.assertFalse(audit("Hello {name}","Hallo")["ok"])
    def test_ids(self):
        rows=audit_tables({1:"%s",2:"hello"},{1:"%d",3:"new"})
        self.assertEqual([r["status"] for r in rows],["placeholder-mismatch","missing-id","extra-id"])
