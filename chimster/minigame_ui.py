"""Neutral local minigame editor; no native game execution."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .minigames import validate,load,export
from pathlib import Path
def mount(parent):
    ident=tk.StringVar(value="ExampleGame");title=tk.StringVar(value="Cargo Run")
    for label,v in (("Project ID",ident),("Title",title)):
        r=ttk.Frame(parent);r.pack(fill="x")
        ttk.Label(r,text=label,width=12).pack(side="left");ttk.Entry(r,textvariable=v).pack(side="left",fill="x",expand=True)
    ttk.Label(parent,text="# wall | . floor | S start | C collectible | E exit").pack(anchor="w")
    editor=tk.Text(parent,wrap="none",font=("TkFixedFont",12));editor.pack(fill="both",expand=True)
    editor.insert("1.0","#######\n#S.C.E#\n#######")
    def project():
        return validate({"schema":1,"id":ident.get(),"title":title.get(),"map":editor.get("1.0","end-1c").splitlines()})
    def open_game(dropped=None):
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Minigame project","*.json")])
        if not p:return
        try:
            data=load(p);ident.set(data["id"]);title.set(data["title"]);editor.delete("1.0","end");editor.insert("1.0","\n".join(data["map"]))
        except (ValueError,OSError) as e:messagebox.showerror("Minigame",str(e))
    def check():
        try:project();messagebox.showinfo("Minigame","Map is valid and objectives are reachable.")
        except ValueError as e:messagebox.showerror("Minigame",str(e))
    def write():
        p=filedialog.askdirectory(title="Choose parent for new minigame folder")
        if not p:return
        try:
            data=project();target=Path(p)/data["id"];export(data,target);messagebox.showinfo("Minigame",str(target/"play.html"))
        except (OSError,ValueError) as e:messagebox.showerror("Minigame",str(e))
    bar=ttk.Frame(parent);bar.pack(fill="x")
    for label,fn in (("Open project",open_game),("Validate",check),("Export playable preview",write)):ttk.Button(bar,text=label,command=fn).pack(side="left")
    from .drop_import import editor_drop
    editor_drop(parent,[([".json"],open_game,False)])
