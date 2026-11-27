"""Desktop translation workbench, explicit source/catalog binding."""
import json,tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from .project import read_json
from .localization import TranslationMemory
from . import localization_project as loc
def mount(parent):
    source=None;catalog=None;selected=None
    bar=ttk.Frame(parent);bar.pack(fill="x")
    state=tk.StringVar(value="Open a source project to create or load a matching catalog.")
    ttk.Label(parent,textvariable=state,wraplength=900).pack(fill="x")
    pane=ttk.Panedwindow(parent,orient="horizontal");pane.pack(fill="both",expand=True)
    left=ttk.Frame(pane);pane.add(left,weight=1)
    lst=tk.Listbox(left,exportselection=False);lst.pack(fill="both",expand=True)
    right=ttk.Frame(pane);pane.add(right,weight=2)
    ttk.Label(right,text="Source").pack(anchor="w")
    original=tk.Text(right,height=6,wrap="word",state="disabled");original.pack(fill="both",expand=True)
    ttk.Label(right,text="Translation").pack(anchor="w")
    target=tk.Text(right,height=6,wrap="word");target.pack(fill="both",expand=True)
    encoding=tk.StringVar(value="utf-8");ttk.Combobox(bar,textvariable=encoding,values=("utf-8","cp1252"),state="readonly",width=9).pack(side="right")
    keys=[]
    def guard(fn):
        def run():
            try:fn()
            except (ValueError,OSError,KeyError,TypeError) as e:messagebox.showerror("Localization",str(e))
        return run
    def store():
        if selected is not None and catalog is not None:
            value=target.get("1.0","end-1c")
            if value or not catalog["entries"][selected]["source"]:catalog["entries"][selected]["target"]=value
            else:catalog["entries"][selected]["target"]=None
    def refresh():
        nonlocal selected
        selected=None;keys[:]=sorted(catalog["entries"]) if catalog else []
        lst.delete(0,"end");target.delete("1.0","end")
        original.configure(state="normal");original.delete("1.0","end");original.configure(state="disabled")
        for k in keys:lst.insert("end",k)
        if catalog:
            n=sum(e["target"] is not None for e in catalog["entries"].values())
            state.set(f'{catalog["source_lang"]} → {catalog["target_lang"]}: {n}/{len(keys)} filled')
    def choose(event=None):
        nonlocal selected
        if not lst.curselection():return
        store();selected=keys[lst.curselection()[0]];e=catalog["entries"][selected]
        original.configure(state="normal");original.delete("1.0","end");original.insert("1.0",e["source"]);original.configure(state="disabled")
        target.delete("1.0","end");target.insert("1.0",e["target"] or "")
    def open_source():
        nonlocal source,catalog
        p=filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if p:source=read_json(Path(p));catalog=None;refresh();state.set(Path(p).name+" loaded")
    def create():
        nonlocal catalog
        if source is None:raise ValueError("open source first")
        kind=simpledialog.askstring("Source kind","book / quest / native-quest / records")
        if not kind:return
        a=simpledialog.askstring("Source language","Language code",initialvalue="en")
        if not a:return
        b=simpledialog.askstring("Target language","Language code")
        if not b:return
        catalog=loc.catalog(kind,source,a,b);refresh()
    def load():
        nonlocal catalog
        if source is None:raise ValueError("open source first")
        p=filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if p:catalog=loc.verified(read_json(Path(p)),source);refresh()
    def save(value):
        p=filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            with Path(p).open("x",encoding="utf-8") as f:json.dump(value,f,ensure_ascii=False,indent=2)
    def ensure():
        if catalog is None:raise ValueError("create or open catalog first")
        store()
    def check():
        ensure();r=loc.check(catalog,source,encoding.get());messagebox.showinfo("Validation",json.dumps(r,ensure_ascii=False,indent=2)[:12000])
    def memory_op(reuse):
        nonlocal catalog
        ensure();p=filedialog.asksaveasfilename(title="Translation memory database",defaultextension=".sqlite",confirmoverwrite=False)
        if not p:return
        m=TranslationMemory(p)
        try:
            if reuse:
                catalog,n=loc.reuse(catalog,source,m);refresh()
                messagebox.showinfo("Memory",f"Reused {n} exact matches.")
            else:messagebox.showinfo("Memory",f"Saved {loc.remember(catalog,source,m,encoding.get())} approved entries.")
        finally:m.close()
    for label,fn in (("Open source",open_source),("New catalog",create),("Load catalog",load),("Save catalog",lambda:(ensure(),save(catalog))),("Reuse memory",lambda:memory_op(True)),("Validate",check),("Remember",lambda:memory_op(False)),("Export translation",lambda:(ensure(),save(loc.apply(catalog,source,encoding.get()))))):
        ttk.Button(bar,text=label,command=guard(fn)).pack(side="left")
    lst.bind("<<ListboxSelect>>",choose)
