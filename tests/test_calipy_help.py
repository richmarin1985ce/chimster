import unittest
from chimster.calipy_help import LocalHelp, make_cards

class FakeWiki:
    data = {"nav.md": "# Navigation\n## Generate navmesh\n- Select a cell.\n- Review generated mesh before export.",
            "script.md": "# Script compiler\n## Compile scripts\nChoose the compiler.\nRead diagnostics."}
    def pages(self):
        return [{"id": key, "title": value.splitlines()[0][2:]} for key,value in self.data.items()]
    def read(self, key):
        return {"body": self.data[key]}

class LocalHelpTests(unittest.TestCase):
    def setUp(self):
        self.help = LocalHelp(FakeWiki())
    def test_contextual_document(self):
        guide = self.help.find("How do I generate navmeshes?")[0]
        self.assertEqual(guide.page, "nav.md")
        self.assertEqual(guide.cards, ("• Select a cell.", "• Review generated mesh before export."))
    def test_alias_and_unknown(self):
        self.assertEqual(self.help.find("compiling scripts")[0].page, "script.md")
        self.assertEqual(self.help.find("unicorn astrophysics"), ())
        self.assertEqual(self.help.find("how do I"), ())
    def test_source_text(self):
        self.assertEqual(" ".join(make_cards(["hello world"])), "hello world")
