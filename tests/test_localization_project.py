import unittest
from chimster.localization_project import catalog,reuse,apply,check,remember
from chimster.localization import TranslationMemory
class LocalizationTests(unittest.TestCase):
    def test_book_and_memory(self):
        p={"schema":1,"editor_id":"Book","title":"Hello","author":"","pages":["Hello {name}"],"game":"newvegas","kind":"book"}
        c=catalog("book",p,"en","es");self.assertFalse(check(c,p)["valid"])
        c["entries"]["Book.title"]["target"]="Hola";c["entries"]["Book.page.0001"]["target"]="Hola {name}"
        m=TranslationMemory(":memory:")
        try:
            remember(c,p,m);fresh,n=reuse(catalog("book",p,"en","es"),p,m)
            self.assertEqual(n,2);self.assertEqual(apply(fresh,p)["pages"],["Hola {name}"])
            fresh["entries"]["Book.page.0001"]["target"]="Hola"
            self.assertFalse(check(fresh,p)["valid"])
            with self.assertRaises(ValueError):apply(fresh,{**p,"title":"Changed"})
        finally:m.close()
    def test_native(self):
        p={"schema":1,"id":"Quest","title":"Quest","stages":[{"index":0,"log":"Start"}],"topics":[{"id":"Ask","prompt":"Ask","responses":[{"id":"Reply","text":"Hello","conditions":[{"stage":0,"done":True}]}]}]}
        c=catalog("native-quest",p,"en","es")
        for e in c["entries"].values():e["target"]="Hola"
        q=apply(c,p);self.assertEqual(q["topics"][0]["responses"][0]["conditions"],p["topics"][0]["responses"][0]["conditions"])
        self.assertEqual(q["topics"][0]["responses"][0]["text"],"Hola")
