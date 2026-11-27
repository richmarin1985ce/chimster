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

    def test_native_fields(self):
        from chimster.localization_fields import extract,replace
        p={"schema":1,"id":"Quest","title":"Title","stages":[{"index":0,"log":"Begin","actions":[{"op":"stage","index":1}]}],"topics":[{"id":"Talk","prompt":"Talk","responses":[{"id":"Reply","lines":[{"text":"Hello","emotion":1}],"choices":["Other"]}]}]}
        values={k:v+"!" for k,v,_ in extract("native-quest",p)}
        q=replace("native-quest",p,values)
        self.assertEqual(q["topics"][0]["responses"][0]["lines"][0]["text"],"Hello!")
        self.assertEqual(q["topics"][0]["responses"][0]["choices"],["Other"])
        self.assertEqual(q["stages"][0]["actions"],p["stages"][0]["actions"])
        self.assertEqual(p["title"],"Title")
