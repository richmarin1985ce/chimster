"""Read-only desktop compatibility workbench."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .game_installations import GAMES,inspect as installation
from .compatibility_audit import audit
from .compatibility_dependencies import validate
from .compatibility_policy import capabilities
from .native_profiles import canonical_profile
from .compatibility_archives import inspect as archive
from .compatibility_nif import inspect as nif
from .compatibility_strings import parse

def mount(parent,game=None):
    profile=tk.StringVar(value="new-vegas")
    def sync(*_):
        if game is not None:
            try:target=canonical_profile(game.get())
            except ValueError:return
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
    def choose(fn,limit=None,dropped=None):
        path=dropped if dropped is not None else filedialog.askopenfilename()
        if path:
            with open(path,"rb") as stream:data=stream.read() if limit is None else stream.read(limit)
            return fn(Path(path),data)
    def root(dropped=None):
        path=dropped if dropped is not None else filedialog.askdirectory()
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
    def precedence():
        from .archive_overlay import build_profile,conflicts
        from tkinter import simpledialog
        paths=filedialog.askopenfilenames(title="Select available archives",filetypes=[("Archives","*.bsa *.ba2")])
        if not paths:return
        order=simpledialog.askstring("Plugin order","Plugin filenames in low-to-high order, separated by commas")
        if order is None:return
        config=filedialog.askopenfilename(title="Select game INI (cancel to omit)",filetypes=[("INI","*.ini")])
        loose=filedialog.askdirectory(title="Select loose asset directory (cancel to omit)")
        policy="exclude"
        if loose:
            choice=messagebox.askyesnocancel("Loose assets","Place loose assets above archives? No places them below.")
            if choice is None:return
            policy="last" if choice else "first"
        overlay=build_profile(profile.get(),[p.strip() for p in order.split(",") if p.strip()],paths,
                              config=config or None,loose=[loose] if loose else [],loose_policy=policy)
        query=simpledialog.askstring("Conflict filter","Filter conflicting asset paths (blank for all)")
        if query is None:return
        result=conflicts(overlay,query)
        return {**{k:v for k,v in overlay.items() if k!="catalog"},"conflicts":result}
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
    def package_archive():
        from .archive_packaging import package_directory
        from tkinter import messagebox
        formats={"oblivion":("103",".bsa"),"fallout3":("104",".bsa"),"new-vegas":("104",".bsa"),"skyrim":("104",".bsa"),"skyrim-se":("105",".bsa"),"skyrim-vr":("105",".bsa"),"morrowind":("tes3",".bsa"),"fallout4":("ba2",".ba2"),"fallout4-vr":("ba2",".ba2")}
        if profile.get() not in formats:raise ValueError("Archive writing is not available for this game profile")
        fmt,suffix=formats[profile.get()]
        if fmt=='ba2' and messagebox.askyesno('Automatic packaging','Automatically separate general assets and DDS textures into a pair of archives?'):
            fmt='pair'
        if fmt=='ba2':
            choice=messagebox.askyesnocancel('BA2 archive type','Create a texture-only DX10 archive?\nYes: DDS textures only.\nNo: general-purpose archive.')
            if choice is None:return
            if choice:fmt='dx10'
        ba2_version=1
        if fmt in ("ba2","dx10","pair") and profile.get()=="fallout4":
            from tkinter import simpledialog
            ba2_version=simpledialog.askinteger("BA2 version","Archive version: 1 (original), 7 or 8 (newer Fallout 4)",initialvalue=1,minvalue=1,maxvalue=8)
            if ba2_version is None:return
            if ba2_version not in (1,7,8):raise ValueError("Select version 1, 7 or 8")
        source=filedialog.askdirectory(title="Select original mod asset directory")
        if not source:return
        if fmt=="pair":
            from pathlib import Path
            from tkinter import simpledialog
            folder=filedialog.askdirectory(title="Select output directory")
            if not folder:return
            stem=simpledialog.askstring("Mod name","Enter plugin basename without extension")
            if not stem:return
            if any(c in stem for c in "/\\:") or stem in (".",".."):raise ValueError("Invalid mod name")
            target=str(Path(folder)/stem)
        else:
            target=filedialog.asksaveasfilename(defaultextension=suffix,filetypes=[("Game archive","*"+suffix)])
        if not target:return
        if not messagebox.askyesno("Experimental archive packaging","Package all files in the selected directory? Use only assets you are authorized to distribute. Retail compatibility is unverified."):return
        compress=fmt!="tes3" and messagebox.askyesno("Compression","Compress assets when beneficial? BSA 105 compression requires LZ4.")
        return package_directory(source,target,format=fmt,compress=compress,ba2_version=ba2_version)
    def validate_archive():
        from .archive_validation import audit
        source=filedialog.askopenfilename(filetypes=[("Archives","*.bsa *.ba2")])
        if source:return audit(source)
    def compare_archive():
        from .archive_external_validation import compare
        source=filedialog.askopenfilename(filetypes=[("Archives","*.bsa *.ba2")])
        if not source:return
        reference=filedialog.askdirectory(title="Select independently extracted reference assets")
        if reference:return compare(source,reference)
    actions=ttk.Frame(parent);actions.pack(fill="x")
    for label,fn in [
        ("Package archive",package_archive),("Validate archive",validate_archive),("Compare reference",compare_archive),("Export member",export_member),("Packed assets",packed_assets),("Asset lookup",assets),("Archive conflicts",precedence),("Installation",root),("Capabilities",lambda:capabilities(profile.get())),
        ("Plugin",lambda:choose(lambda p,d:audit(profile.get(),d))),
        ("Dependencies",dependencies),("Archive header",lambda:choose(lambda p,d:archive(d),36)),
        ("NIF header",lambda:choose(lambda p,d:nif(d),256)),
        ("String table",lambda:choose(lambda p,d:{"strings":parse(d,p.suffix)}))]:
        ttk.Button(actions,text=label,command=lambda f=fn:run(f)).pack(side="left")
    profile.trace_add("write",lambda *_:show(capabilities(profile.get())))
    show(capabilities(profile.get()))
    from .drop_import import editor_drop
    editor_drop(parent,[
        ((".esp",".esm",".esl",".omwaddon",".omwgame"),lambda p:run(lambda:choose(lambda name,data:audit(profile.get(),data),dropped=p)),False),
        ((".bsa",".ba2"),lambda p:run(lambda:choose(lambda name,data:archive(data),36,dropped=p)),False),
        ((".nif",),lambda p:run(lambda:choose(lambda name,data:nif(data),256,dropped=p)),False),
        ((".strings",".dlstrings",".ilstrings"),lambda p:run(lambda:choose(lambda name,data:{"strings":parse(data,name.suffix)},dropped=p)),False),
        (("<directory>",),lambda p:run(lambda:root(p)),False)
    ],confirm=False)
