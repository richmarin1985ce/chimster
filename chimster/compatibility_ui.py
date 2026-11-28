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
        from .compatibility_asset_lookup import index,resolve
        from tkinter import simpledialog
        layers=[]
        while True:
            folder=filedialog.askdirectory(title="Add loose asset layer (lowest precedence first; Cancel to finish)")
            if not folder:break
            root=Path(folder)
            layers.append((str(root),[(p.relative_to(root).as_posix(),str(p)) for p in root.rglob("*") if p.is_file() and not p.is_symlink()]))
        if not layers:return None
        catalog=index(layers)
        query=simpledialog.askstring("Asset lookup","Relative asset path")
        if query:return resolve(catalog,query)
        return {"indexed_paths":len(catalog),"layers":[name for name,_ in layers]}
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
    actions=ttk.Frame(parent);actions.pack(fill="x")
    for label,fn in [
        ("Packed assets",packed_assets),("Asset lookup",assets),("Installation",root),("Capabilities",lambda:capabilities(profile.get())),
        ("Plugin",lambda:choose(lambda p,d:audit(profile.get(),d))),
        ("Dependencies",dependencies),("Archive header",lambda:choose(lambda p,d:archive(d),36)),
        ("NIF header",lambda:choose(lambda p,d:nif(d),256)),
        ("String table",lambda:choose(lambda p,d:{"strings":parse(d,p.suffix)}))]:
        ttk.Button(actions,text=label,command=lambda f=fn:run(f)).pack(side="left")
    profile.trace_add("write",lambda *_:show(capabilities(profile.get())))
    show(capabilities(profile.get()))
