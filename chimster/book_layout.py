"""Portable illustrated book layout. Does not claim game-specific font or markup support."""
from pathlib import Path
import html,json,shutil
from .books import Book,save
from .atlas import write_png
FONTS={"serif":"Georgia,serif","sans":"system-ui,sans-serif","mono":"monospace"}
def export(book,layout,assets,output):
    book.validate()
    if layout.get("schema")!=1 or set(layout)-{"schema","font","alignment","cover","illustrations"}:raise ValueError("unsupported book layout")
    font=layout.get("font","serif");align=layout.get("alignment","left")
    if font not in FONTS or align not in {"left","center","justify"}:raise ValueError("invalid layout")
    images=layout.get("illustrations",[])
    if not isinstance(images,list) or len(images)>len(book.pages)*4:raise ValueError("invalid illustrations")
    root=Path(assets).resolve(strict=True);dest=Path(output)
    if not root.is_dir() or dest.exists() or dest.is_symlink() or dest.resolve().is_relative_to(root):raise ValueError("use a fresh output outside the asset folder")
    planned=[]
    for i in images:
        if set(i)!={"page","image","caption"} or type(i["page"]) is not int or not 1<=i["page"]<=len(book.pages) or not isinstance(i["caption"],str):raise ValueError("invalid illustration")
        planned.append(i)
    if "cover" in layout:
        planned.insert(0,{"page":0,"image":layout["cover"],"caption":book.title})
    from PIL import Image
    converted=[]
    for i,row in enumerate(planned):
        name=row["image"]
        if not isinstance(name,str) or "\\" in name or ":" in name or any(p in ("",".","..") for p in name.split("/")):raise ValueError("unsafe image path")
        src=root/name
        if src.is_symlink() or not src.resolve(strict=True).is_relative_to(root) or not src.is_file():raise ValueError("unsafe source image")
        with Image.open(src) as im:
            if not 1<=im.width<=4096 or not 1<=im.height<=4096 or im.width*im.height>8_000_000:raise ValueError("image exceeds limit")
            im.thumbnail((1200,1200));im=im.convert("RGBA")
            converted.append((row,f"image-{i:03d}.png",im.width,im.height,im.tobytes()))
    dest.mkdir(parents=True,exist_ok=False)
    try:
        save(book,dest/"book.json");(dest/"layout.json").write_text(json.dumps(layout,ensure_ascii=False,indent=2),encoding="utf-8")
        def picture(row,name):
            return '<figure><img src="'+name+'" alt="'+html.escape(row["caption"],quote=True)+'"><figcaption>'+html.escape(row["caption"])+'</figcaption></figure>'
        rendered={}
        for row,name,w,h,rgba in converted:
            write_png(dest/name,w,h,rgba);rendered.setdefault(row["page"],[]).append(picture(row,name))
        page_html=[]
        for n,p in enumerate(book.pages,1):
            body="".join("<p>"+html.escape(t).replace("\n","<br>")+"</p>" for t in p.split("\n\n"))
            page_html.append("<section>"+body+"".join(rendered.get(n,[]))+f"<footer>{n} / {len(book.pages)}</footer></section>")
        css="body{background:#34312c;color:#241d17;font:18px "+FONTS[font]+"}section,header{max-width:650px;margin:24px auto;padding:38px;background:#f2e6cb;text-align:"+align+"}img{max-width:100%;height:auto}footer,figcaption{text-align:center;font-size:13px}p{overflow-wrap:anywhere}"
        out="<!doctype html><meta charset=utf-8><title>Book preview</title><style>"+css+"</style><header><h1>"+html.escape(book.title)+"</h1><p>"+html.escape(book.author)+"</p>"+"".join(rendered.get(0,[]))+"</header>"+"".join(page_html)
        (dest/"preview.html").write_text(out,encoding="utf-8")
        (dest/"localization.json").write_text(json.dumps(book.localization(),ensure_ascii=False,indent=2),encoding="utf-8")
    except Exception:shutil.rmtree(dest);raise
    return {"output":str(dest),"pages":len(book.pages),"images":len(converted),"scope":"portable illustrated preview; native engine markup and cover meshes not generated"}
