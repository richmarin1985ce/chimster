"""Local FUZ container workbench; no audio transcoding."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .audio import pack_fuz,unpack_fuz

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
        lip,audio=read();status.set(f"Version 1; lip {len(lip)} bytes; audio {len(audio)} bytes")
    def pack():
        audio=Path(values["Audio source"].get()).read_bytes()
        lip=Path(values["Lip source"].get()).read_bytes() if values["Lip source"].get() else b""
        blob=pack_fuz(audio,lip);unpack_fuz(blob)
        p=filedialog.asksaveasfilename(defaultextension=".fuz")
        if p:
            with Path(p).open("xb") as f:f.write(blob)
            status.set("Created "+p)
    def extract():
        lip,audio=read()
        folder=filedialog.askdirectory()
        if not folder:return
        target=Path(folder)/(Path(values["FUZ source"].get()).stem+"-extracted")
        target.mkdir()
        if lip:(target/"voice.lip").write_bytes(lip)
        (target/"voice.xwm").write_bytes(audio)
        status.set("Extracted to "+str(target))
    def guard(fn):
        def run():
            try:fn()
            except (OSError,ValueError) as e:messagebox.showerror("Voice containers",str(e))
        return run
    for label,fn in (("Inspect FUZ",inspect),("Pack FUZ",pack),("Extract FUZ",extract)):
        ttk.Button(parent,text=label,command=guard(fn)).pack(anchor="w")

    from .audio_edit_ui import launch as launch_editor
    ttk.Button(parent,text="Open waveform and lip-sync editor",command=lambda:launch_editor(parent)).pack(anchor="w")
    from .voice_record_ui import launch as launch_recording
    ttk.Button(parent,text="Record and manage takes",command=lambda:launch_recording(parent)).pack(anchor="w")
    ttk.Separator(parent).pack(fill="x", pady=8)
    mount_voice_manager(parent)


def mount_voice_manager(parent):
    import json
    import threading
    import queue
    from . import voice_manager, audio
    frame=ttk.LabelFrame(parent,text="Dialogue voice manager",padding=5)
    frame.pack(fill="both",expand=True)
    values={k:tk.StringVar() for k in ("Voice root","Manifest","Output root","Encoder","FFmpeg","LIP tool","Fonix data")}
    for name,v in values.items():
        row=ttk.Frame(frame);row.pack(fill="x")
        ttk.Label(row,text=name,width=14).pack(side="left")
        ttk.Entry(row,textvariable=v).pack(side="left",fill="x",expand=True)
        def choose(name=name,v=v):
            p=filedialog.askdirectory() if name in ("Voice root","Output root") else filedialog.askopenfilename()
            if p:v.set(p)
        ttk.Button(row,text="Browse",command=choose).pack(side="left")
    controls=ttk.Frame(frame);controls.pack(fill="x")
    tree=ttk.Treeview(frame,columns=("record","status","detail"),show="headings",height=6)
    for column,label,width in (("record","Record / voice line",230),("status","Status",110),("detail","Detail",420)):
        tree.heading(column,text=label);tree.column(column,width=width)
    tree.pack(fill="both",expand=True)
    status=tk.StringVar();ttk.Label(frame,textvariable=status).pack(anchor="w")
    q=queue.Queue()
    buttons=[]
    def show(result):
        tree.delete(*tree.get_children())
        rows=result.get("lines",result.get("results",[]))
        for row in rows:
            tree.insert("", "end",values=(row.get("record","")+" | "+row["stem"],row["status"],row.get("error",row.get("text",row.get("operation","")))))
        errors=result.get("errors",result.get("inventory_errors",[]))
        for error in errors:tree.insert("","end",values=(error["path"],"invalid",error["error"]))
        status.set(f"{len(rows)} lines; {len(errors)} inventory errors")
    def poll():
        try:kind,value=q.get_nowait()
        except queue.Empty:
            if frame.winfo_exists():frame.after(100,poll)
            return
        for b in buttons:b.configure(state="normal")
        if kind=="error":
            status.set("Operation failed");messagebox.showerror("Voice manager",value)
        else:show(value)
    def start(mode):
        settings={k:v.get().strip() for k,v in values.items()}
        if not settings["Voice root"] or not settings["Manifest"] or (mode!="audit" and not settings["Output root"]):
            messagebox.showerror("Voice manager","Choose source, manifest and (for batch) a separate output root.");return
        if mode=="execute" and not messagebox.askyesno("Build voices","Run the configured local tools and create new staged FUZ files?"):return
        def run():
            try:
                manifest=voice_manager.load_manifest(settings["Manifest"])
                if mode=="audit":result=voice_manager.audit(settings["Voice root"],manifest)
                else:result=voice_manager.batch_pack(settings["Voice root"],settings["Output root"],manifest,
                    encoder=settings["Encoder"] or None,ffmpeg=settings["FFmpeg"] or None,
                    lip_tool=settings["LIP tool"] or None,fonix=settings["Fonix data"] or None,execute=mode=="execute")
                q.put(("ok",result))
            except Exception as exc:q.put(("error",str(exc)))
        for b in buttons:b.configure(state="disabled")
        status.set("Processing...");threading.Thread(target=run,daemon=True).start();frame.after(100,poll)
    for label,mode in (("Audit voice lines","audit"),("Preview batch","plan"),("Build staged FUZ","execute")):
        b=ttk.Button(controls,text=label,command=lambda mode=mode:start(mode));b.pack(side="left");buttons.append(b)
