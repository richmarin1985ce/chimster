"""Local phoneme workbench with explicit import, editing and calibration actions."""
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from . import phoneme_import as pi,morph_calibration as mc,audio

def launch(parent):
    win=tk.Toplevel(parent);win.title("Chimster — Phonemes and morph calibration");win.geometry("880x650")
    state={"rows":[],"duration":None,"wav":None};busy=[False];q=queue.Queue();buttons=[]
    status=tk.StringVar(value="Select audio to define the timeline duration.")
    bar=ttk.Frame(win);bar.pack(fill="x")
    tree=ttk.Treeview(win,columns=("phoneme","start","end","confidence"),show="headings")
    for c in ("phoneme","start","end","confidence"):tree.heading(c,text=c.title())
    tree.pack(fill="both",expand=True,padx=8,pady=8)
    edit=ttk.Frame(win);edit.pack(fill="x")
    fields=[tk.StringVar() for _ in range(3)]
    for name,var in zip(("Phoneme","Start","End"),fields):
        ttk.Label(edit,text=name).pack(side="left");ttk.Entry(edit,textvariable=var,width=14).pack(side="left")
    ttk.Label(win,textvariable=status,wraplength=850).pack(anchor="w")
    def guard(fn):
        def run(*_):
            try:fn()
            except Exception as exc:messagebox.showerror("Phonemes",str(exc),parent=win)
        return run
    def require():
        if state["duration"] is None:raise ValueError("Choose WAV first")
        return state["duration"]
    def refresh():
        tree.delete(*tree.get_children())
        for i,r in enumerate(state["rows"]):tree.insert("","end",iid=str(i),values=(r["phoneme"],r["start"],r["end"],r.get("confidence","")))
        status.set(f'{len(state["rows"])} intervals; {require():.3f} seconds')
    def wav():
        p=filedialog.askopenfilename(parent=win,filetypes=[("WAV","*.wav")])
        if p:
            duration=audio.wav_info(Path(p).read_bytes())["duration"]
            state.update(wav=p,duration=duration,rows=[]);refresh()
    def imported():
        duration=require()
        p=filedialog.askopenfilename(parent=win,filetypes=[("Phoneme timing","*.json *.csv *.tsv *.TextGrid"),("All files","*")])
        if not p:return
        tier="phones"
        if Path(p).suffix.lower()==".textgrid":
            tier=simpledialog.askstring("Interval tier","Exact phoneme tier name",initialvalue="phones",parent=win)
            if tier is None:return
        state["rows"]=pi.load(p,duration,tier);refresh()
    def select(*_):
        if tree.selection():
            for v,x in zip(fields,tree.item(tree.selection()[0],"values")):v.set(x)
    def modify(mode):
        rows=list(state["rows"])
        sel=tree.selection()
        if mode!="add" and not sel:raise ValueError("Select interval")
        if mode=="remove":del rows[int(sel[0])]
        else:
            row=dict(phoneme=fields[0].get(),start=float(fields[1].get()),end=float(fields[2].get()))
            if mode=="add":rows.append(row)
            else:rows[int(sel[0])]=row
        rows.sort(key=lambda r:r["start"])
        state["rows"]=pi.validate(rows,require()) if rows else [];refresh()
    def save():
        duration=require()
        p=filedialog.asksaveasfilename(parent=win,defaultextension=".json")
        if p:pi.save(p,state["rows"],duration)
    def poll():
        try:kind,value=q.get_nowait()
        except queue.Empty:win.after(100,poll);return
        busy[0]=False
        for b in buttons:b.configure(state="normal")
        if kind=="error":status.set(value);return
        if kind=="alignment":state["rows"]=value;refresh()
        elif kind=="native":status.set("Experimental native LIP and receipt saved; verify in game.")
        else:status.set("Calibration probes created; observe them in-game and fill observations.json.")
    def start(kind,fn):
        if busy[0]:return
        busy[0]=True
        for b in buttons:b.configure(state="disabled")
        status.set("Running selected local tool...")
        def work():
            try:q.put((kind,fn()))
            except Exception as e:q.put(("error",str(e)))
        threading.Thread(target=work,daemon=True).start();win.after(100,poll)
    def align():
        require()
        transcript=simpledialog.askstring("Transcript","Exact recorded dialogue",parent=win)
        if not transcript:return
        dictionary=filedialog.askopenfilename(parent=win,title="Local MFA pronunciation dictionary")
        if not dictionary:return
        model=filedialog.askopenfilename(parent=win,title="Local MFA acoustic model")
        if not model:return
        source=state["wav"]
        start("alignment",lambda:pi.align(source,transcript,dictionary,model))
    def probes():
        p=filedialog.asksaveasfilename(parent=win,title="New calibration directory")
        if p and messagebox.askyesno("Experimental probes","Generate 33 Skyrim test LIPs with local OpenFaceFX?",parent=win):
            start("probes",lambda:mc.probes(p))
    def choose_profile(force=False):
        if not force and state.get("profile") is not None:return state["profile"]
        p=filedialog.askopenfilename(parent=win,title="Observed morph profile",filetypes=[("JSON","*.json")])
        if not p:return None
        cal=mc.profile(json.loads(Path(p).read_text(encoding="utf-8")))
        state["profile"]=cal;status.set("Loaded morph profile: "+Path(p).name)
        return cal
    def preview():
        duration=require()
        cal=choose_profile()
        if cal is None:return
        data=mc.preview(state["rows"],duration,cal)
        out=filedialog.asksaveasfilename(parent=win,defaultextension=".json")
        if out:audio.publish(Path(out),json.dumps(data,indent=2,ensure_ascii=False).encode())
    from . import drop_import as di
    def dropped(paths):
        if busy[0]:raise ValueError("Finish current operation first")
        found=di.classify(paths);tier="phones"
        if "timeline" in found and found["timeline"].suffix.lower()==".textgrid":
            tier=simpledialog.askstring("Interval tier","Exact phoneme tier name",initialvalue="phones",parent=win)
            if tier is None:return
        if "wav" in found and state["rows"] and "timeline" not in found:
            if not messagebox.askyesno("Replace WAV","Replace audio and clear its phoneme timeline?",parent=win):return
        updated=di.load_bundle(paths,state,tier=tier)
        state.update(updated)
        if state["duration"] is not None:refresh()
        status.set("Imported "+", ".join(p.name for p in paths))
    if di.bind_files(tree,dropped,lambda msg:messagebox.showerror("Drop import",msg,parent=win)):
        ttk.Label(win,text="Drop WAV, phoneme timeline and/or profile onto the table.").pack(anchor="w")
    else:
        ttk.Label(win,text="File drop unavailable; use Browse or install the dragdrop extra.").pack(anchor="w")
    def character_preview():
        duration=require()
        cal=choose_profile()
        if cal is None:return
        from .face_preview_ui import launch as launch_face
        launch_face(win,list(state["rows"]),duration,cal,state["wav"])
    def profile_editor():
        from .morph_profile_ui import launch as launch_profile
        launch_profile(win)
    def native_export():
        require()
        cal=choose_profile()
        if cal is None:return
        out=filedialog.asksaveasfilename(parent=win,title="Choose NEW output directory name")
        if not out:return
        if not messagebox.askyesno("Experimental native export","Generate a Skyrim LIP from the observed slot mapping? In-game verification is required.",parent=win):return
        from .phoneme_synthesis import build
        rows=list(state["rows"]);source=state["wav"]
        start("native",lambda:build(source,rows,cal,out,experimental=True))
    tools=ttk.Frame(win);tools.pack(fill="x")
    for label,fn in (("Load profile",lambda:choose_profile(True)),("Edit morph profile",profile_editor),("Export native Skyrim LIP",native_export),("Character preview",character_preview)):
        b=ttk.Button(tools,text=label,command=guard(fn));b.pack(side="left");buttons.append(b)
    for label,fn in (("Open WAV",wav),("Import phonemes",imported),("Save timeline",save),("MFA align",align),("Generate probes",probes),("Mapped preview",preview)):
        b=ttk.Button(bar,text=label,command=guard(fn));b.pack(side="left");buttons.append(b)
    for label,mode in (("Add","add"),("Edit","edit"),("Delete","remove")):
        b=ttk.Button(edit,text=label,command=guard(lambda mode=mode:modify(mode)));b.pack(side="left");buttons.append(b)
    tree.bind("<<TreeviewSelect>>",select)
    def close():
        if busy[0]:messagebox.showinfo("Phonemes","Wait for local operation to finish.",parent=win)
        else:win.destroy()
    win.protocol("WM_DELETE_WINDOW",close)
