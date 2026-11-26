"""Local book authoring tab. No game writes."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .books import Book,GAMES,load,export
def mount(parent):
    fields={k:tk.StringVar(value=v) for k,v in {"editor_id":"ChimsterBook","title":"Untitled","author":"","kind":"book","game":"newvegas"}.items()}
    for k,var in fields.items():
        row=ttk.Frame(parent);row.pack(fill="x",pady=2)
        ttk.Label(row,text=k,width=12).pack(side="left")
        if k in ("kind","game"):ttk.Combobox(row,textvariable=var,values=("book","note","journal") if k=="kind" else sorted(GAMES),state="readonly").pack(side="left",fill="x",expand=True)
        else:ttk.Entry(row,textvariable=var).pack(side="left",fill="x",expand=True)
    ttk.Label(parent,text="Separate pages with a line containing ---PAGE---. Plain text; preview is not the game font/layout.").pack(anchor="w")
    text=tk.Text(parent,wrap="word");text.pack(fill="both",expand=True)
    def book():
        import re
        return Book(**{k:v.get() for k,v in fields.items()},pages=tuple(re.split(r"\n---PAGE---\n",text.get("1.0","end-1c")))).validate()
    def open_book():
        p=filedialog.askopenfilename(filetypes=[("Book project","*.json")])
        if not p:return
        try:
            b=load(p)
            for k,v in fields.items():v.set(getattr(b,k))
            text.delete("1.0","end");text.insert("1.0","\n---PAGE---\n".join(b.pages))
        except (OSError,ValueError,TypeError) as e:messagebox.showerror("Book",str(e))
    def write():
        parentdir=filedialog.askdirectory(title="Choose parent for new book output")
        if not parentdir:return
        try:
            b=book();p=Path(parentdir)/b.editor_id;export(b,p)
            messagebox.showinfo("Book exported",str(p))
        except (OSError,ValueError,TypeError) as e:messagebox.showerror("Book",str(e))
    def validate():
        try:b=book();messagebox.showinfo("Book",f"{len(b.pages)} pages; {sum(map(len,b.pages))} characters. Valid portable project.")
        except (ValueError,TypeError) as e:messagebox.showerror("Book",str(e))
    def native():
        from .fnv_content import export_book
        from tkinter import simpledialog
        try:
            b=book();model=None
            if b.kind=="book":
                model=simpledialog.askstring("Book model","Relative NIF path under meshes (required)")
                if not model:return
            p=filedialog.asksaveasfilename(defaultextension=".esp",filetypes=[("New Vegas plugin","*.esp")])
            if not p:return
            export_book(b,p,model);messagebox.showinfo("Experimental ESP",p+"\nValidate in xEdit and game before use.")
        except (ValueError,TypeError,OSError) as e:messagebox.showerror("Book",str(e))
    bar=ttk.Frame(parent);bar.pack(fill="x")
    for label,cmd in [("Open",open_book),("Validate",validate),("Export project + preview",write),("Export FNV ESP",native)]:ttk.Button(bar,text=label,command=cmd).pack(side="left")
