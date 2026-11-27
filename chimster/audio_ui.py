"""Local FUZ container workbench; no audio transcoding."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .formats import pack_fuz,unpack_fuz

def mount(parent):
    ttk.Label(parent,text="Voice containers — existing encoded audio and lip-sync data").pack(anchor="w")
    values={k:tk.StringVar() for k in ("FUZ source","Audio source","Lip source")}
    for name,v in values.items():
        row=ttk.Frame(parent);row.pack(fill="x")
        ttk.Label(row,text=name,width=16).pack(side="left")
        ttk.Entry(row,textvariable=v).pack(side="left",fill="x",expand=True)
        def choose(v=v):
            p=filedialog.askopenfilename()
            if p:v.set(p)
        ttk.Button(row,text="Browse",command=choose).pack(side="left")
    status=tk.StringVar();ttk.Label(parent,textvariable=status).pack(anchor="w")
    def read():
        return unpack_fuz(Path(values["FUZ source"].get()).read_bytes())
    def inspect():
        version,lip,audio=read();status.set(f"Version {version}; lip {len(lip)} bytes; audio {len(audio)} bytes")
    def pack():
        audio=Path(values["Audio source"].get()).read_bytes()
        lip=Path(values["Lip source"].get()).read_bytes() if values["Lip source"].get() else b""
        blob=pack_fuz(lip,audio);unpack_fuz(blob)
        p=filedialog.asksaveasfilename(defaultextension=".fuz")
        if p:
            with Path(p).open("xb") as f:f.write(blob)
            status.set("Created "+p)
    def extract():
        _,lip,audio=read()
        folder=filedialog.askdirectory()
        if not folder:return
        target=Path(folder)/(Path(values["FUZ source"].get()).stem+"-extracted")
        target.mkdir()
        (target/"voice.lip").write_bytes(lip)
        (target/"audio.bin").write_bytes(audio)
        status.set("Extracted to "+str(target))
    def guard(fn):
        def run():
            try:fn()
            except (OSError,ValueError) as e:messagebox.showerror("Voice containers",str(e))
        return run
    for label,fn in (("Inspect FUZ",inspect),("Pack FUZ",pack),("Extract FUZ",extract)):
        ttk.Button(parent,text=label,command=guard(fn)).pack(anchor="w")
