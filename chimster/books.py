"""Portable in-game book and note authoring. Does not write engine plugin records."""
from dataclasses import dataclass,asdict
from pathlib import Path
import json,re,html

GAMES={"morrowind","openmw","oblivion","fallout3","newvegas","skyrim","skyrimse","skyrimvr","fallout4","fallout4vr","starfield"}
ID=re.compile(r"[A-Za-z][A-Za-z0-9_]{0,63}")
@dataclass(frozen=True)
class Book:
    editor_id:str
    title:str
    pages:tuple
    author:str=""
    kind:str="book"
    game:str="newvegas"
    def validate(self):
        if not isinstance(self.editor_id,str) or not ID.fullmatch(self.editor_id):raise ValueError("invalid editor ID")
        if self.game not in GAMES or self.kind not in {"book","note","journal"}:raise ValueError("unsupported game or type")
        if not isinstance(self.title,str) or not self.title.strip() or len(self.title)>256 or not isinstance(self.author,str) or len(self.author)>256:raise ValueError("invalid title or author")
        if not isinstance(self.pages,(tuple,list)) or not 1<=len(self.pages)<=500 or any(not isinstance(p,str) or len(p)>16000 or "\0" in p for p in self.pages):raise ValueError("invalid pages")
        if sum(map(len,self.pages))>256000:raise ValueError("book exceeds size limit")
        return self
    def localization(self):
        self.validate()
        return {self.editor_id+".title":self.title,self.editor_id+".author":self.author,**{f"{self.editor_id}.page.{i:04d}":p for i,p in enumerate(self.pages,1)}}
    def translated(self,strings):
        source=self.localization()
        if set(strings)!=set(source):raise ValueError("localization IDs must match exactly")
        return Book(self.editor_id,strings[self.editor_id+".title"],tuple(strings[f"{self.editor_id}.page.{i:04d}"] for i in range(1,len(self.pages)+1)),strings[self.editor_id+".author"],self.kind,self.game).validate()

def save(book,path):
    book.validate()
    with Path(path).open("x",encoding="utf-8") as f:json.dump({"schema":1,**asdict(book)},f,ensure_ascii=False,indent=2)
def load(path):
    p=Path(path)
    if p.stat().st_size>4*1024*1024:raise ValueError("book file too large")
    data=json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or data.pop("schema",None)!=1:raise ValueError("unsupported book schema")
    if isinstance(data.get("pages"),list):data["pages"]=tuple(data["pages"])
    return Book(**data).validate()

def preview(book):
    book.validate()
    def esc(s):return html.escape(s,quote=True)
    pages=[]
    for n,text in enumerate(book.pages,1):
        body="".join("<p>"+esc(p).replace("\n","<br>")+"</p>" for p in text.split("\n\n"))
        pages.append(f'<section><header>{esc(book.title)}</header>{body}<footer>{n} / {len(book.pages)}</footer></section>')
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Book preview</title><style>body{background:#322b23;color:#35271d;font:18px Georgia,serif;margin:24px}h1,p{overflow-wrap:anywhere}h1,aside{color:#f3e7cb;text-align:center}section{box-sizing:border-box;max-width:650px;min-height:420px;padding:42px;margin:24px auto;background:#efe3c5;box-shadow:0 4px 12px #17130f}header,footer{font:13px system-ui;color:#766047}footer{text-align:center;margin-top:32px}@media print{body{background:white}section{break-after:page;box-shadow:none}}</style>"""+f"<h1>{esc(book.title)}</h1><aside>{esc(book.author)}</aside>"+"".join(pages)+"</html>"

def export(book,folder):
    book.validate()
    p=Path(folder);p.mkdir(parents=True,exist_ok=False)
    save(book,p/"book.json")
    (p/"localization.json").write_text(json.dumps(book.localization(),ensure_ascii=False,indent=2),encoding="utf-8")
    (p/"preview.html").write_text(preview(book),encoding="utf-8")
    (p/"body.txt").write_text("\n\n".join(book.pages),encoding="utf-8")
    return {"output":str(p),"pages":len(book.pages),"status":"portable authoring assets; native game record export pending"}
