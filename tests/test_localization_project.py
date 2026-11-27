import unittest,json
from tempfile import TemporaryDirectory
from pathlib import Path
from chimster.localization_project import catalog,review,remember,suggest,apply,pack_native
class LocalizationTests(unittest.TestCase):
    def test_review_and_reuse(self):
        with TemporaryDirectory() as d:
            p=Path(d);q=p/"strings.json";q.write_text(json.dumps({"1":"Hello {name}","2":"Hello {name}"}))
            c=catalog("strings",q);c["src_lang"]="en";c["dst_lang"]="fr"
            c["entries"][0].update(target="Bonjour {name}",status="approved")
            c["entries"][1].update(target="Salut {name}",status="approved")
            remember(c,p/"memory.sqlite")
            r=suggest(catalog("strings",q),p/"memory.sqlite","en","fr")
            self.assertEqual([x["target"] for x in r["entries"]],["Bonjour {name}","Salut {name}"])
            self.assertFalse(review(r)["valid"])
            for e in r["entries"]:e["status"]="approved"
            apply(r,q,p/"out.json");pack_native(p/"out.json",p/"out.strings","STRINGS","utf-8")
            r["entries"][0]["target"]="Bonjour"
            self.assertFalse(review(r)["valid"])
