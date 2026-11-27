"""Safe offline Markdown subset, shared by the desktop reader and HTML export.
No HTML interpretation, external resource fetching or code execution."""
import re,html,posixpath
from urllib.parse import unquote
INLINE=re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)|\x60([^\x60\n]+)\x60|\*\*([^*\n]+)\*\*")
def heading_id(s):
    return re.sub(r"[^\w-]","",re.sub(r"\s+","-",s.strip().casefold()))
def target(page,url,pages):
    url=unquote(url)
    if any(c in url for c in ("\\",":","\0","?")) or url.startswith("/"):return None
    path,_,fragment=url.partition("#")
    p=posixpath.normpath(posixpath.join(posixpath.dirname(page),path)) if path else page
    if p not in pages:return None
    return p,fragment
def inline(s,page,pages):
    out=[];last=0
    for m in INLINE.finditer(s):
        if m.start()>last:out.append(("text",s[last:m.start()],None))
        if m[1] is not None:out.append(("link",m[1],target(page,m[2],pages)))
        elif m[3] is not None:out.append(("code",m[3],None))
        else:out.append(("bold",m[4],None))
        last=m.end()
    if last<len(s):out.append(("text",s[last:],None))
    return out
def blocks(body):
    fence=None
    for line in body.splitlines():
        if line.startswith(("~~~","\x60\x60\x60")):
            if fence is None:fence=line[:3]
            elif line.startswith(fence):fence=None
            else:yield "code",line,None
            continue
        if fence:yield "code",line,None;continue
        h=re.match(r"^(#{1,6})\s+(.+)$",line)
        if h:yield "h"+str(len(h[1])),h[2],heading_id(h[2]);continue
        m=re.match(r"^\s*[-*]\s+(.*)$",line)
        if m:yield "list","• "+m[1],None;continue
        yield "text",line,None
def render_html(page,body,pages,filename):
    esc=html.escape
    out=["<!doctype html><html><meta charset='utf-8'><meta name='viewport' content='width=device-width'><title>"+esc(page)+"</title><style>body{font:16px system-ui;max-width:960px;margin:2rem auto;padding:0 1rem;line-height:1.55;color:#20262b}code,pre{background:#eef1f4;font-family:monospace}pre{white-space:pre-wrap;padding:.15rem .5rem;margin:0}a{color:#225b87}p{margin:.35rem 0}h1,h2,h3{margin-top:1.1em}</style><nav><a href='index.html'>Contents</a></nav>"]
    anchors={}
    for kind,s,anchor in blocks(body):
        if kind=="code":out.append("<pre>"+esc(s)+"</pre>");continue
        parts=[]
        for style,label,dest in inline(s,page,pages):
            value=esc(label)
            if style=="link" and dest:
                url=filename[dest[0]]+("#"+dest[1] if dest[1] else "")
                value="<a href='"+esc(url,quote=True)+"'>"+value+"</a>"
            elif style=="code":value="<code>"+value+"</code>"
            elif style=="bold":value="<strong>"+value+"</strong>"
            parts.append(value)
        tag=kind if kind in {"h1","h2","h3","h4","h5","h6"} else "p"
        if anchor is not None:
            n=anchors.get(anchor,0);anchors[anchor]=n+1
            anchor=anchor+("-"+str(n) if n else "")
        attr=" id='"+esc(anchor,quote=True)+"'" if anchor is not None else ""
        out.append("<"+tag+attr+">"+"".join(parts)+"</"+tag+">")
    return "\n".join(out)+"</html>"
def export(wiki,folder):
    from pathlib import Path
    import hashlib
    p=Path(folder);p.mkdir(parents=True,exist_ok=False)
    rows=wiki.pages();ids={r["id"] for r in rows};names={k:"page-"+hashlib.sha256(k.encode()).hexdigest()[:24]+".html" for k in ids}
    for r in rows:(p/names[r["id"]]).write_text(render_html(r["id"],wiki.read(r["id"])["body"],ids,names),encoding="utf-8")
    index="<!doctype html><meta charset='utf-8'><title>Chimster manual</title><h1>Chimster manual</h1><ul>"+"".join("<li><a href='"+names[r["id"]]+"'>"+html.escape(r["title"])+"</a></li>" for r in rows)+"</ul>"
    (p/"index.html").write_text(index,encoding="utf-8")
    return {"pages":len(rows),"index":str(p/"index.html"),"scope":"safe Markdown subset; external links displayed as text"}
def audit(wiki):
    ids={r["id"] for r in wiki.pages()};anchors={}
    for k in ids:
        seen={};values=set()
        for _,_,a in blocks(wiki.read(k)["body"]):
            if a is not None:
                n=seen.get(a,0);seen[a]=n+1;values.add(a+("-"+str(n) if n else ""))
        anchors[k]=values
    broken=[];external=0
    for k in sorted(ids):
        for kind,s,_ in blocks(wiki.read(k)["body"]):
            if kind=="code":continue
            for m in INLINE.finditer(s):
                if m[1] is None:continue
                url=m[2]
                if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:",url):external+=1;continue
                t=target(k,url,ids)
                if not t or t[1] and t[1] not in anchors[t[0]]:broken.append({"page":k,"target":url})
    return {"pages":len(ids),"broken_links":broken,"external_links_not_checked":external}
