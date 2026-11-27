"""Small safe Markdown renderer and relative documentation link resolver.
No remote content, raw HTML, JavaScript, or embedded images are loaded."""
from pathlib import PurePosixPath
from urllib.parse import unquote,urlsplit
import re,html,posixpath
LINK=re.compile(r'\[([^\]\n]+)\]\(([^)\n]+)\)|\x60([^\x60\n]+)\x60|\*\*([^*\n]+)\*\*|\*([^*\n]+)\*')
def resolve(page,target,pages):
    if not isinstance(target,str) or len(target)>2048:return None
    try:u=urlsplit(target)
    except ValueError:return None
    if u.scheme or u.netloc or u.query:return None
    raw=unquote(u.path)
    if "\\" in raw or raw.startswith("/") or "\0" in raw:return None
    dest=posixpath.normpath(posixpath.join(posixpath.dirname(page),raw)) if raw else page
    if dest==".." or dest.startswith("../") or dest not in pages:return None
    return dest
def blocks(body):
    """Conservative subset, represented as semantic blocks for both HTML and Tk."""
    if not isinstance(body,str) or len(body)>1024*1024:raise ValueError("document too large")
    result=[];code=None
    for line in body.splitlines():
        if line.lstrip().startswith("\x60\x60\x60"):
            if code is None:code=[]
            else:result.append(("code","\n".join(code)));code=None
            continue
        if code is not None:code.append(line);continue
        if line.startswith("    "):result.append(("code",line[4:]));continue
        m=re.match(r"^(#{1,6})\s+(.*)$",line)
        if m:result.append(("h"+str(len(m[1])),m[2]));continue
        if re.match(r"^\s*[-*+]\s+",line):result.append(("bullet",re.sub(r"^\s*[-*+]\s+","",line)));continue
        if line.startswith("> "):result.append(("quote",line[2:]));continue
        result.append(("p",line))
    if code is not None:result.append(("code","\n".join(code)))
    return result
def spans(text):
    pos=0
    for m in LINK.finditer(text):
        if m.start()>pos:yield ("plain",text[pos:m.start()],None)
        if m[1]:yield ("link",m[1],m[2])
        elif m[3]:yield ("code",m[3],None)
        elif m[4]:yield ("bold",m[4],None)
        else:yield ("italic",m[5],None)
        pos=m.end()
    if pos<len(text):yield ("plain",text[pos:],None)
def heading_ids(body):
    used=set()
    for kind,text in blocks(body):
        if not kind.startswith('h'):continue
        base=re.sub(r'[^\w-]', '', re.sub(r'\s+', '-', text.strip().casefold())) or 'section'
        anchor=base;n=1
        while anchor in used:
            anchor=f'{base}-{n}';n+=1
        used.add(anchor)
        yield anchor

def render(page,body,pages):
    result=[];anchors=iter(heading_ids(body))
    for kind,text in blocks(body):
        if kind=="code":result.append("<pre><code>"+html.escape(text)+"</code></pre>");continue
        parts=[]
        for style,value,target in spans(text):
            safe=html.escape(value)
            if style=="link":
                dest=resolve(page,target,pages)
                if dest:
                    rel=posixpath.relpath(dest+".html",posixpath.dirname(page) or ".")
                    fragment=urlsplit(target).fragment
                    if fragment:rel+='#'+fragment
                    safe='<a href="'+html.escape(rel,quote=True)+'">'+safe+'</a>'
            elif style in {"code","bold","italic"}:
                tag={"code":"code","bold":"strong","italic":"em"}[style];safe=f"<{tag}>{safe}</{tag}>"
            parts.append(safe)
        tag=kind if kind.startswith("h") else "blockquote" if kind=="quote" else "p"
        attr=\' id="\'+html.escape(next(anchors),quote=True)+\'"\' if kind.startswith("h") else ""
        result.append(f"<{tag}{attr}>"+("• " if kind=="bullet" else "")+"".join(parts)+f"</{tag}>")
    return "<!doctype html><html><meta charset='utf-8'><title>Local manual</title><style>body{font:17px system-ui;max-width:850px;margin:2rem auto;padding:1rem}pre{white-space:pre-wrap;background:#eee;padding:1rem}code{font-family:monospace}blockquote{border-left:3px solid #777;padding-left:1rem}</style><body>"+"\n".join(result)+"</body></html>"
def link_report(wiki):
    pages={p["id"] for p in wiki.pages()};broken=[];internal=0;external=0
    anchors={p:set(heading_ids(wiki.read(p)["body"])) for p in pages}
    for page in sorted(pages):
        for kind,line in blocks(wiki.read(page)["body"]):
            if kind=="code":continue
            for style,value,target in spans(line):
                if style!="link":continue
                dest=resolve(page,target,pages)
                try:u=urlsplit(target)
                except ValueError:
                    broken.append({"page":page,"target":target});continue
                if dest and (not u.fragment or unquote(u.fragment) in anchors[dest]):internal+=1
                elif u.scheme in ("https","http"):external+=1
                else:broken.append({"page":page,"target":target})
    return {"pages":len(pages),"internal_links":internal,"external_links_not_fetched":external,"unresolved_links":broken}
def export(wiki,folder):
    from pathlib import Path
    p=Path(folder);p.mkdir(parents=True,exist_ok=False);pages=wiki.pages();ids={r["id"] for r in pages}
    for page in pages:
        q=p/(page["id"]+".html");q.parent.mkdir(parents=True,exist_ok=True)
        q.write_text(render(page["id"],wiki.read(page["id"])["body"],ids),encoding="utf-8")
    links="".join('<li><a href="'+html.escape(r["id"]+".html",quote=True)+'">'+html.escape(r["title"])+"</a></li>" for r in pages)
    (p/"index.html").write_text("<!doctype html><meta charset=utf-8><title>Chimster manual</title><h1>Manual</h1><ul>"+links+"</ul>",encoding="utf-8")
    return {"output":str(p),**link_report(wiki)}
