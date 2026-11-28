import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import threading,queue,tempfile
from pathlib import Path
from . import voice_record as vr,voice_takes as vt,audio_edit as ae

def launch(parent):
    win=tk.Toplevel(parent);win.title("Chimster — Voice takes");win.geometry("850x550")
    values={k:tk.StringVar() for k in ("Registry","Line stem","Performer","Rights","Staging","Seconds")}
    values["Seconds"].set("10")
    from .drop_import import path_field
    for name,v in values.items():
        row=ttk.Frame(win);row.pack(fill="x")
        ttk.Label(row,text=name,width=14).pack(side="left");field=ttk.Entry(row,textvariable=v);field.pack(side="left",fill="x",expand=True)
        if name=="Registry":path_field(field,v,directory=True)
        if name in ("Registry","Staging"):
            def choose(v=v):
                p=filedialog.askdirectory(parent=win)
                if p:v.set(p)
            ttk.Button(row,text="Browse",command=choose).pack(side="left")
    bar=ttk.Frame(win);bar.pack(fill="x")
    dev=ttk.Combobox(bar,state="readonly",width=40);dev.pack(side="left")
    tree=ttk.Treeview(win,columns=("line","performer","seconds","rights"),show="headings")
    for c in ("line","performer","seconds","rights"):tree.heading(c,text=c)
    tree.pack(fill="both",expand=True)
    status=tk.StringVar(value="Select a microphone explicitly before recording.")
    ttk.Label(win,textvariable=status).pack(anchor="w")
    q=queue.Queue();cancel=threading.Event();busy=[False];buttons=[];player=[None]
    def guard(fn):
        def run():
            try:fn()
            except Exception as exc:messagebox.showerror("Voice takes",str(exc),parent=win)
        return run
    def settings():
        s={k:v.get().strip() for k,v in values.items()}
        if not all(s[k] for k in ("Registry","Line stem","Performer","Rights")):raise ValueError("Registry, line, performer and permission basis required")
        from .voice_manager import stem
        stem(s["Line stem"]);return s
    def register(s,path):
        return vt.register(s["Registry"],path,line=s["Line stem"],performer=s["Performer"],rights=s["Rights"])
    def refresh():
        root=values["Registry"].get().strip()
        if not root:raise ValueError("Choose registry")
        tree.delete(*tree.get_children())
        if Path(root).exists():
            for r in vt.list_takes(root):tree.insert("","end",iid=r["id"],values=(r["line"],r["performer"],round(r["info"]["duration"],2),r["rights"]))
    def discover():
        dev.configure(values=[f'{d["index"]}: {d["name"]}' for d in vr.devices()]);dev.set("")
    def imported():
        s=settings();p=filedialog.askopenfilename(parent=win,filetypes=[("WAV","*.wav")])
        if p:register(s,p);refresh()
    def selected():
        if not tree.selection():raise ValueError("Select a take")
        return tree.selection()[0]
    def stop():
        p=player[0]
        if p and p.poll() is None:p.terminate()
        player[0]=None
    def preview():
        root=values["Registry"].get().strip();ident=selected();vt.get(root,ident)
        stop();player[0]=ae.play(Path(root)/ident/"take.wav")
    def stage():
        root=values["Registry"].get().strip();dest=values["Staging"].get().strip()
        if not root or not dest:raise ValueError("Choose registry and staging")
        status.set(vt.select(root,selected(),dest)["path"])
    def poll():
        try:kind,result=q.get_nowait()
        except queue.Empty:
            win.after(100,poll);return
        busy[0]=False
        for b in buttons:b.configure(state="normal")
        status.set(result if kind=="error" else "Saved take "+result["id"])
        if kind=="ok":guard(refresh)()
    def capture():
        s=settings()
        if not dev.get():raise ValueError("Choose input device")
        index=int(dev.get().split(":",1)[0]);duration=float(s["Seconds"])
        if not messagebox.askyesno("Record",f"Record {duration:g} seconds from selected input?",parent=win):return
        busy[0]=True;cancel.clear();status.set("Recording — cancel to discard")
        for b in buttons:b.configure(state="disabled")
        def work():
            try:
                data=vr.record(duration,index,cancelled=cancel.is_set)
                if cancel.is_set():raise ValueError("Recording discarded")
                with tempfile.TemporaryDirectory() as t:
                    p=Path(t)/"capture.wav";p.write_bytes(data);result=register(s,p)
                q.put(("ok",result))
            except Exception as exc:q.put(("error",str(exc)))
        threading.Thread(target=work,daemon=True).start();win.after(100,poll)
    for label,fn in (("Devices",discover),("Record",capture),("Import WAV",imported),("Refresh",refresh),("Play",preview),("Stage",stage)):
        b=ttk.Button(bar,text=label,command=guard(fn));b.pack(side="left");buttons.append(b)
    ttk.Button(win,text="Cancel recording",command=cancel.set).pack(anchor="w")
    def close():
        if busy[0]:cancel.set();status.set("Cancelling; close when recording stops.");return
        stop();win.destroy()
    win.protocol("WM_DELETE_WINDOW",close)
