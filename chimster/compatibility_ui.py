"""Read-only desktop compatibility workbench."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .game_installations import GAMES,inspect as installation
from .compatibility_audit import audit
from .compatibility_dependencies import validate
from .compatibility_policy import capabilities
from .compatibility_archives import inspect as archive
from .compatibility_nif import inspect as nif
from .compatibility_strings import parse

def mount(parent,game=None):
    profile=tk.StringVar(value="new-vegas")
    aliases={"newvegas":"new-vegas","skyrimse":"skyrim-se","skyrimvr":"skyrim-vr","fallout4vr":"fallout4-vr"}
    def sync(*_):
        if game is not None:
            target=aliases.get(game.get(),game.get())
            if target in GAMES:profile.set(target)
    if game is not None:game.trace_add("write",sync);sync()
    bar=ttk.Frame(parent);bar.pack(fill="x")
    ttk.Label(bar,text="Target game").pack(side="left")
    ttk.Combobox(bar,textvariable=profile,values=list(GAMES),state="readonly").pack(side="left")
    tree=ttk.Treeview(parent,columns=("value",),show="tree headings")
    tree.heading("#0",text="Property");tree.heading("value",text="Value")
    tree.pack(fill="both",expand=True)
    def show(value):
        tree.delete(*tree.get_children())
        def add(parent,key,val):
            branch=isinstance(val,(dict,list,tuple))
            node=tree.insert(parent,"end",text=str(key),values=("" if branch else str(val),),open=True)
            if branch:
                for k,v in (val.items() if isinstance(val,dict) else enumerate(val)):add(node,k,v)
        for k,v in value.items():add("",k,v)
    def run(fn):
        try:
            result=fn()
            if result is not None:show(result)
        except (OSError,ValueError,KeyError) as exc:messagebox.showerror("Compatibility",str(exc))
    def choose(fn,limit=None):
        path=filedialog.askopenfilename()
        if path:
            with open(path,"rb") as stream:data=stream.read() if limit is None else stream.read(limit)
            return fn(Path(path),data)
    def root():
        path=filedialog.askdirectory()
        if path:return installation(path,profile.get())
    def dependencies():
        paths=filedialog.askopenfilenames(title="Select plugins in load order; review displayed order")
        if paths:return validate(profile.get(),[(Path(p).name,Path(p).read_bytes()) for p in paths])
    def assets():
        from .archive_overlay import build
        from .compatibility_asset_lookup import resolve
        from tkinter import simpledialog
        win=tk.Toplevel(parent);win.title("Asset layers — lowest priority first")
        sources=[]
        cached={}
        listing=tk.Listbox(win,width=85,height=10);listing.pack(fill="both",expand=True)
        def refresh():
            listing.delete(0,"end")
            for source in sources:listing.insert("end",source)
        def add(packed):
            path=filedialog.askopenfilename(parent=win,filetypes=[("Archives","*.bsa *.ba2")]) if packed else filedialog.askdirectory(parent=win)
            if path and path not in sources:sources.append(path);refresh()
        def move(delta):
            sel=listing.curselection()
            if not sel:return
            i=sel[0];j=i+delta
            if 0<=j<len(sources):
                sources[i],sources[j]=sources[j],sources[i];refresh();listing.selection_set(j)
        def remove():
            sel=listing.curselection()
            if sel:sources.pop(sel[0]);refresh()
        def lookup():
            query=simpledialog.askstring("Asset lookup","Relative asset path",parent=win)
            if query:
                def search():
                    key=tuple(sources)
                    if cached.get("sources")!=key:
                        catalog=build(sources)
                        cached.update(sources=key,catalog=catalog)
                    return resolve(cached["catalog"],query)
                run(search)
        buttons=ttk.Frame(win);buttons.pack(fill="x")
        for label,fn in [("Add archive",lambda:add(True)),("Add directory",lambda:add(False)),("Up",lambda:move(-1)),("Down",lambda:move(1)),("Remove",remove),("Refresh index",lambda:cached.clear()),("Find asset",lookup)]:
            ttk.Button(buttons,text=label,command=fn).pack(side="left")
        ttk.Label(win,text="Last layer wins in this preview; actual game precedence may differ.").pack()
        return None
    def packed_assets():
        from .archive_reader import directory,read
        from tkinter import simpledialog
        archive_path=filedialog.askopenfilename(filetypes=[("Archives","*.bsa *.ba2")])
        if not archive_path:return None
        entries=directory(archive_path)
        query=simpledialog.askstring("Archive browser","Filter member paths (blank for first 500)")
        if query is None:return None
        matches=[name for name in entries if query.casefold().replace("\\\\","/") in name]
        return {"archive":archive_path,"total":len(entries),"matches":len(matches),"members":matches[:500]}
    def export_member():
        from .archive_reader import read
        from tkinter import simpledialog
        source=filedialog.askopenfilename(filetypes=[("Archives","*.bsa *.ba2")])
        if not source:return
        name=simpledialog.askstring("Archive member","Exact relative member path")
        if not name:return
        data=read(source,name)
        target=filedialog.asksaveasfilename(initialfile=Path(name.replace(chr(92),"/")).name)
        if target:
            with open(target,"xb") as stream:stream.write(data)
            return {"exported":target,"bytes":len(data)}
    actions=ttk.Frame(parent);actions.pack(fill="x")
    for label,fn in [
        ("Export member",export_member),("Packed assets",packed_assets),("Asset lookup",assets),("Installation",root),("Capabilities",lambda:capabilities(profile.get())),
        ("Plugin",lambda:choose(lambda p,d:audit(profile.get(),d))),
        ("Dependencies",dependencies),("Archive header",lambda:choose(lambda p,d:archive(d),36)),
        ("NIF header",lambda:choose(lambda p,d:nif(d),256)),
        ("String table",lambda:choose(lambda p,d:{"strings":parse(d,p.suffix)}))]:
        ttk.Button(actions,text=label,command=lambda f=fn:run(f)).pack(side="left")
    profile.trace_add("write",lambda *_:show(capabilities(profile.get())))
    show(capabilities(profile.get()))
