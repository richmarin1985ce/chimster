"""Interactive CPU-rendered 3D facial morph preview."""
import math,time
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from . import face_preview as fp,audio_edit as ae,drop_import as di

def launch(parent,rows,duration,profile,wav=None):
    win=tk.Toplevel(parent);win.title("Chimster — Character facial preview");win.geometry("780x650")
    state={"rig":None,"grid":None,"playing":False,"start":0.,"offset":0.,"yaw":0.,"pitch":0.,"zoom":1.,"anchor":None,"player":None,"bounds":None,"timer":None}
    bar=ttk.Frame(win);bar.pack(fill="x")
    canvas=tk.Canvas(win,bg="#22272d",highlightthickness=0);canvas.pack(fill="both",expand=True)
    status=tk.StringVar(value="Load a local rig JSON with base OBJ and matching morph targets.")
    ttk.Label(win,textvariable=status).pack(anchor="w")
    slider=ttk.Scale(win,from_=0,to=duration);slider.pack(fill="x")
    audio_on=tk.BooleanVar(value=False)
    ttk.Checkbutton(bar,text="Audio (FFplay)",variable=audio_on).pack(side="left")
    def guard(fn):
        def run(*args):
            try:return fn(*args)
            except Exception as exc:messagebox.showerror("Character preview",str(exc),parent=win)
        return run
    def render():
        if state["rig"] is None:return
        t=float(slider.get());index=min(len(state["grid"])-1,round(t*30))
        weights=state["grid"][index];rig=state["rig"]
        canvas.delete("all")
        for _,points,color in fp.project(rig.pose(weights),rig.triangles,max(1,canvas.winfo_width()),max(1,canvas.winfo_height()),state["yaw"],state["pitch"],state["zoom"],state["bounds"]):
            canvas.create_polygon(*points,fill=color,outline="")
        label=next((r["phoneme"] for r in rows if r["start"]<=t<r["end"]),"sil")
        status.set(f"{t:.2f} s / {duration:.2f} s | {label} | portable rig preview, not in-game verification")
    def stop():
        state["playing"]=False
        if state["timer"] is not None:
            win.after_cancel(state["timer"]);state["timer"]=None
        p=state["player"]
        if p and p.poll() is None:p.terminate()
        state["player"]=None
    def load(path):
        rig=fp.load(path);grid=fp.animation(rig,rows,duration,profile)
        if len(rig.triangles)>5000:raise ValueError("Preview supports up to 5000 triangles for interactive drawing")
        stop()
        lo=[min(v[j] for v in rig.base) for j in range(3)];hi=[max(v[j] for v in rig.base) for j in range(3)]
        state.update(rig=rig,grid=grid,bounds=([(a+b)/2 for a,b in zip(lo,hi)],max(b-a for a,b in zip(lo,hi)) or 1))
        slider.set(0);render()
    def browse():
        p=filedialog.askopenfilename(parent=win,filetypes=[("Rig manifest","*.json")])
        if p:load(p)
    def drop(paths):
        if len(paths)!=1:raise ValueError("Drop one rig JSON")
        load(paths[0])
    def tick():
        state["timer"]=None
        if not state["playing"]:return
        t=state["offset"]+time.monotonic()-state["start"]
        slider.set(min(t,duration));render()
        if t>=duration:stop()
        else:state["timer"]=win.after(33,tick)
    def play():
        if not state["rig"]:raise ValueError("Load a rig")
        stop();offset=float(slider.get())
        if offset>=duration:offset=0
        if audio_on.get():
            if not wav:raise ValueError("No audio source")
            state["player"]=ae.play(wav,offset,duration)
        state.update(playing=True,start=time.monotonic(),offset=offset);tick()
    def scrub(_):
        if not state["playing"]:render()
    def begin(e):state["anchor"]=(e.x,e.y)
    def orbit(e):
        if state["anchor"]:
            x,y=state["anchor"];state["yaw"]+=(e.x-x)*.01;state["pitch"]=max(-1.5,min(1.5,state["pitch"]+(e.y-y)*.01));state["anchor"]=(e.x,e.y);render()
    def zoom(delta):
        state["zoom"]=max(.25,min(4,state["zoom"]*delta));render()
    def close():
        stop();win.destroy()
    for name,fn in (("Open rig",browse),("Play",play),("Pause",stop),("Zoom +",lambda:zoom(1.15)),("Zoom −",lambda:zoom(1/1.15))):
        ttk.Button(bar,text=name,command=guard(fn)).pack(side="left")
    slider.configure(command=scrub);slider.bind("<ButtonPress-1>",lambda _:stop())
    canvas.bind("<Configure>",lambda _:render());canvas.bind("<ButtonPress-1>",begin);canvas.bind("<B1-Motion>",orbit)
    canvas.bind("<ButtonRelease-1>",lambda _:state.update(anchor=None))
    di.bind_files(canvas,drop,lambda msg:messagebox.showerror("Rig import",msg,parent=win))
    win.protocol("WM_DELETE_WINDOW",close)
