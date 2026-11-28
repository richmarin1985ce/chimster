"""Local waveform and mouth-cue editor. Never writes original assets."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from . import audio_edit as ae

def launch(parent):
    win=tk.Toplevel(parent);win.title("Chimster — Audio editor");win.geometry("900x640")
    state={"clip":None,"path":None,"env":[],"cues":None,"player":None,"anchor":None}
    start=tk.StringVar(value="0");end=tk.StringVar(value="0")
    gain=tk.StringVar(value="0");fi=tk.StringVar(value="0");fo=tk.StringVar(value="0")
    status=tk.StringVar(value="Open a PCM16 WAV. Normalize other formats using the codec tools.")
    bar=ttk.Frame(win);bar.pack(fill="x")
    canvas=tk.Canvas(win,height=180,bg="#20252c",highlightthickness=0);canvas.pack(fill="x",padx=8,pady=8)
    fields=ttk.Frame(win);fields.pack(fill="x")
    for label,v in (("Start (s)",start),("End (s)",end),("Gain (dB)",gain),("Fade in (s)",fi),("Fade out (s)",fo)):
        ttk.Label(fields,text=label).pack(side="left");ttk.Entry(fields,textvariable=v,width=8).pack(side="left")
    cues=ttk.Treeview(win,columns=("start","end","shape"),show="headings",height=8)
    for c in ("start","end","shape"):cues.heading(c,text=c.title())
    cues.pack(fill="both",expand=True,padx=8)
    edits=ttk.Frame(win);edits.pack(fill="x")
    ca=tk.StringVar();cb=tk.StringVar();shape=tk.StringVar(value="X")
    for v in (ca,cb):ttk.Entry(edits,textvariable=v,width=12).pack(side="left")
    ttk.Combobox(edits,textvariable=shape,values=list("ABCDEFGHX"),state="readonly",width=5).pack(side="left")
    ttk.Label(win,textvariable=status).pack(anchor="w")
    def guard(fn):
        def run(*_):
            try:fn()
            except Exception as exc:messagebox.showerror("Audio editor",str(exc),parent=win)
        return run
    def require():
        if state["clip"] is None:raise ValueError("Open WAV first")
        return state["clip"]
    def selection():
        clip=require();a,b=float(start.get()),float(end.get());clip.selection(a,b);return a,b
    def draw(*_):
        canvas.delete("all")
        clip=state["clip"]
        if not clip:return
        w=max(canvas.winfo_width(),1);h=max(canvas.winfo_height(),1);mid=h*.43
        try:
            a,b=selection();canvas.create_rectangle(a/clip.duration*w,0,b/clip.duration*w,h*.84,fill="#324c62",outline="")
        except ValueError:pass
        canvas.create_line(0,mid,w,mid,fill="#666666")
        for i,(lo,hi) in enumerate(state["env"]):
            x=i*w/max(len(state["env"])-1,1)
            canvas.create_line(x,mid-hi*mid,x,mid-lo*mid,fill="#96c7cf")
        if state["cues"]:
            for c in state["cues"]["mouthCues"]:
                a,b=float(c["start"])/clip.duration*w,float(c["end"])/clip.duration*w
                canvas.create_rectangle(a,h*.85,b,h,fill="#8870a1",outline="#20252c")
                if b-a>14:canvas.create_text((a+b)/2,h*.925,text=c["value"],fill="white")
    def stop():
        p=state["player"]
        if p and p.poll() is None:p.terminate()
        state["player"]=None
    def open_wav():
        path=filedialog.askopenfilename(parent=win,filetypes=[("PCM WAV","*.wav")])
        if not path:return
        clip=ae.Clip.open(path);env=clip.envelope()
        stop();state.update(clip=clip,path=path,env=env,cues=None)
        start.set("0");end.set(str(clip.duration));refresh()
        status.set(f"{Path(path).name} — {clip.duration:.3f} s, {clip.rate} Hz, {clip.channels} channel(s)")
    def preview():
        a,b=selection();stop();state["player"]=ae.play(state["path"],a,b)
    def save():
        a,b=selection();path=filedialog.asksaveasfilename(parent=win,defaultextension=".wav")
        if path:
            require().export(path,a,b,gain_db=float(gain.get()),fade_in=float(fi.get()),fade_out=float(fo.get()))
            status.set("Saved new WAV. Regenerate native LIP for edited audio.")
    def refresh():
        cues.delete(*cues.get_children())
        if state["cues"]:
            for i,c in enumerate(state["cues"]["mouthCues"]):cues.insert("","end",iid=str(i),values=(c["start"],c["end"],c["value"]))
        draw()
    def load_cues():
        clip=require();path=filedialog.askopenfilename(parent=win,filetypes=[("Preview mouth cues","*.json")])
        if path:state["cues"]=ae.read_cues(path,clip.duration);refresh()
    def cue_selected(*_):
        sel=cues.selection()
        if sel:
            a,b,c=cues.item(sel[0],"values");ca.set(a);cb.set(b);shape.set(c)
    def apply_cue():
        sel=cues.selection()
        if not sel:raise ValueError("Select a mouth cue")
        state["cues"]=ae.edit_cue(state["cues"],int(sel[0]),float(ca.get()),float(cb.get()),shape.get(),require().duration);refresh()
    def save_cues(trim=False):
        clip=require()
        if state["cues"] is None:raise ValueError("Load preview cues")
        obj=state["cues"];duration=clip.duration
        if trim:
            a,b=selection();obj=ae.trim_cues(obj,a,b,duration);duration=b-a
        path=filedialog.asksaveasfilename(parent=win,defaultextension=".json")
        if path:ae.export_cues(path,obj,duration)
    def time_at(event):
        return max(0,min(1,event.x/max(canvas.winfo_width(),1)))*require().duration
    def press(event):
        if state["clip"]:state["anchor"]=time_at(event)
    def drag(event):
        if state["anchor"] is not None:
            a,b=sorted((state["anchor"],time_at(event)));start.set(f"{a:.6f}");end.set(str(b));draw()
    def release(event):
        drag(event);state["anchor"]=None
    canvas.bind("<Configure>",draw);canvas.bind("<Button-1>",press);canvas.bind("<B1-Motion>",drag);canvas.bind("<ButtonRelease-1>",release)
    cues.bind("<<TreeviewSelect>>",cue_selected)
    for label,fn in (("Open WAV",open_wav),("Play selection",preview),("Stop",stop),("Export edited WAV",save),("Load cue JSON",load_cues),("Save cues",save_cues),("Export trimmed cues",lambda:save_cues(True))):
        ttk.Button(bar,text=label,command=guard(fn)).pack(side="left")
    ttk.Button(edits,text="Apply preview cue edit",command=guard(apply_cue)).pack(side="left")
    def close():
        stop();win.destroy()
    win.protocol("WM_DELETE_WINDOW",close)
