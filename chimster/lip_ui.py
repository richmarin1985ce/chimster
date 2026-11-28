"""Native LIP generation workbench; outputs are staged and unverified in-game."""
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from . import lip_pipeline as lp

def launch(parent):
    win=tk.Toplevel(parent);win.title("Chimster — Native lip generation");win.geometry("820x610")
    values={k:tk.StringVar() for k in ("WAV","Output directory","Backend executable","Fonix data","FFmpeg")}
    for name,v in values.items():
        row=ttk.Frame(win);row.pack(fill="x",padx=8)
        ttk.Label(row,text=name,width=19).pack(side="left")
        ttk.Entry(row,textvariable=v).pack(side="left",fill="x",expand=True)
        def choose(name=name,v=v):
            p=filedialog.asksaveasfilename(parent=win,title="Choose a NEW output directory name") if name=="Output directory" else filedialog.askopenfilename(parent=win)
            if p:v.set(p)
        ttk.Button(row,text="Browse",command=choose).pack(side="left")
    game=tk.StringVar(value="Skyrim");backend=tk.StringVar(value="facefxwrapper")
    opts=ttk.Frame(win);opts.pack(fill="x")
    ttk.Combobox(opts,textvariable=game,values=("Skyrim","Fallout4"),state="readonly").pack(side="left")
    ttk.Combobox(opts,textvariable=backend,values=("facefxwrapper","openfacefx"),state="readonly").pack(side="left")
    experimental=tk.BooleanVar(value=False)
    ttk.Checkbutton(opts,text="Permit experimental Skyrim export",variable=experimental).pack(side="left")
    ttk.Label(win,text="Dialogue transcript").pack(anchor="w")
    transcript=tk.Text(win,height=5,wrap="word");transcript.pack(fill="x",padx=8)
    result=tk.Text(win,height=12,wrap="word");result.pack(fill="both",expand=True,padx=8)
    bar=ttk.Frame(win);bar.pack(fill="x")
    q=queue.Queue();busy=[False];buttons=[]
    def show(value):
        result.delete("1.0","end");result.insert("1.0",value)
    def poll():
        try:ok,value=q.get_nowait()
        except queue.Empty:win.after(100,poll);return
        busy[0]=False
        for b in buttons:b.configure(state="normal")
        show(json.dumps(value,indent=2) if ok else value)
    def start(op):
        if busy[0]:return
        s={k:v.get().strip() for k,v in values.items()}
        text=transcript.get("1.0","end-1c");g=game.get();b=backend.get();exp=experimental.get()
        if op=="inspect":
            p=filedialog.askopenfilename(parent=win,filetypes=[("Native LIP","*.lip")])
            if not p:return
        elif not s["WAV"] or not s["Output directory"] or not text.strip():
            messagebox.showerror("Native LIP","Choose WAV, output directory and transcript",parent=win);return
        if op=="build" and (not s["Backend executable"] or not messagebox.askyesno("Generate native LIP","Run selected local backend? Output is not game-certified.",parent=win)):return
        busy[0]=True
        for button in buttons:button.configure(state="disabled")
        show("Working with local files...")
        def run():
            try:
                if op=="inspect":value=lp.header(Path(p).read_bytes())
                elif op=="verify":value=lp.verify(s["Output directory"],s["WAV"],text)
                else:value=lp.build(s["WAV"],s["Output directory"],game=g,transcript=text,tool=s["Backend executable"],backend=b,fonix=s["Fonix data"] or None,ffmpeg=s["FFmpeg"] or None,experimental=exp)
                q.put((True,value))
            except Exception as exc:q.put((False,str(exc)))
        threading.Thread(target=run,daemon=True).start();win.after(100,poll)
    for name,op in (("Generate staged LIP","build"),("Verify receipt","verify"),("Inspect native LIP","inspect")):
        b=ttk.Button(bar,text=name,command=lambda op=op:start(op));b.pack(side="left");buttons.append(b)
    def curve_editor():
        from .lip_curve_ui import launch as launch_curves
        launch_curves(win)
    ttk.Button(bar,text="Native curve editor",command=curve_editor).pack(side="left")
    def phonemes():
        from .phoneme_ui import launch as launch_phonemes
        launch_phonemes(win)
    ttk.Button(bar,text="Phonemes and calibration",command=phonemes).pack(side="left")
    def close():
        if busy[0]:messagebox.showinfo("Native LIP","Local operation is running.",parent=win)
        else:win.destroy()
    win.protocol("WM_DELETE_WINDOW",close)
