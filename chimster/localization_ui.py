"""Explicit review of local translations; no external provider or automatic approval."""
import tkinter as tk,json
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from . import localization_project as loc
from .project import read_json
def mount(parent):
    data=None;selected=None;source_path=None
    bar=ttk.Frame(parent);bar.pack(fill="x")
    status=tk.StringVar(value="Open a catalog or extract text from a project.")
    ttk.Label(parent,textvariable=status).pack(fill="x")
    pane=ttk.Panedwindow(parent,orient="horizontal");pane.pack(fill="both",expand=True)
    lst=tk.Listbox(pane,exportselection=False);pane.add(lst,weight=1)
    right=ttk.Frame(pane);pane.add(right,weight=2)
    ttk.Label(right,text="Source").pack(anchor="w")
    source=tk.Text(right,height=8,wrap="word",state="disabled");source.pack(fill="both",expand=True)
    ttk.Label(right,text="Translation").pack(anchor="w")
    translation=tk.Text(right,height=8,wrap="word");translation.pack(fill="both",expand=True)
    def guard(fn):
        def run():
            try:fn()
            except (ValueError,KeyError,TypeError,OSError) as e:messagebox.showerror("Localization",str(e))
        return run
    def refresh():
        nonlocal selected
        selected=None;lst.delete(0,"end")
        if data is None:return
        for r in data["entries"]:lst.insert("end",r["status"]+" | "+r["id"])
        status.set(f'{data["kind"]}: {len(data["entries"])} strings; {sum(r["status"]=="approved" for r in data["entries"])} approved')
        source.configure(state="normal");source.delete("1.0","end");source.configure(state="disabled");translation.delete("1.0","end")
    def select(event=None):
        nonlocal selected
        if not data or not lst.curselection():return
        selected=lst.curselection()[0];r=data["entries"][selected]
        source.configure(state="normal");source.delete("1.0","end");source.insert("1.0",r["source"]);source.configure(state="disabled")
        translation.delete("1.0","end");translation.insert("1.0",r["target"] or "")
    def approve():
        if selected is None:raise ValueError("select a string")
        r=data["entries"][selected];v=translation.get("1.0","end-1c")
        from .localization_audit import audit
        if not audit(r["source"],v)["ok"]:raise ValueError("placeholder mismatch")
        r.update(target=v,status="approved");i=selected;refresh();lst.selection_set(i);lst.see(i);select()
    def open_catalog():
        nonlocal data,source_path
        p=filedialog.askopenfilename(filetypes=[("Catalog JSON","*.json")])
        if p:data=loc.validate(read_json(Path(p)));source_path=None;refresh()
    def extract():
        nonlocal data,source_path
        kind=simpledialog.askstring("Catalog","book / quest / native-quest / records / strings")
        if not kind:return
        p=filedialog.askopenfilename(filetypes=[("Project JSON","*.json")])
        if p:data=loc.catalog(kind,p);source_path=p;refresh()
    def save():
        if data is None:raise ValueError("open a catalog")
        p=filedialog.asksaveasfilename(defaultextension=".json")
        if p:loc.save_json(data,p)
    def suggest():
        nonlocal data
        if data is None:raise ValueError("open a catalog")
        p=filedialog.askopenfilename(title="Translation memory SQLite")
        if not p:return
        src=simpledialog.askstring("Language","Source language",initialvalue=data.get("src_lang","en"))
        if not src:return
        dst=simpledialog.askstring("Language","Target language",initialvalue=data.get("dst_lang",""))
        if dst:data=loc.suggest(data,p,src,dst);refresh()
    def apply():
        if data is None:raise ValueError("open a catalog")
        p=source_path or filedialog.askopenfilename(title="Original source project")
        if not p:return
        encoding=simpledialog.askstring("Encoding","Target encoding",initialvalue="utf-8")
        if not encoding:return
        q=filedialog.asksaveasfilename(defaultextension=".json")
        if q:loc.apply(data,p,q,encoding);messagebox.showinfo("Localization","Translated copy saved.")
    def remember():
        if data is None:raise ValueError("open a catalog")
        src=simpledialog.askstring("Language","Source language",initialvalue=data.get("src_lang","en"))
        if not src:return
        dst=simpledialog.askstring("Language","Target language",initialvalue=data.get("dst_lang",""))
        if not dst:return
        if data.get("src_lang",src)!=src or data.get("dst_lang",dst)!=dst:raise ValueError("catalog language mismatch")
        p=filedialog.asksaveasfilename(title="Translation memory database",defaultextension=".sqlite",confirmoverwrite=False)
        if p:data.update(src_lang=src,dst_lang=dst);loc.remember(data,p);refresh()
    lst.bind("<<ListboxSelect>>",select)
    for name,fn in (("Extract",extract),("Open",open_catalog),("Save",save),("Suggest",suggest),("Approve",approve),("Remember",remember),("Apply",apply)):
        ttk.Button(bar,text=name,command=guard(fn)).pack(side="left")
