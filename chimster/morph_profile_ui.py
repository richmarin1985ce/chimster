"""Edit reusable calibration profiles without manually editing JSON."""
import copy,json
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from . import audio,morph_calibration as mc

def empty():
    return {"schema":1,"game":"Skyrim","observations":{str(s):{"observed":False,"morph":"","notes":""} for s in range(33)},"phonemes":{}}

def launch(parent):
    win=tk.Toplevel(parent);win.title("Chimster — Morph profile");win.geometry("900x650")
    state={"profile":empty()}
    bar=ttk.Frame(win);bar.pack(fill="x")
    slots=ttk.Treeview(win,columns=("observed","morph","notes"),show="tree headings",height=8)
    slots.heading("#0",text="Slot")
    for c in ("observed","morph","notes"):slots.heading(c,text=c.title())
    slots.pack(fill="both",expand=True)
    edit=ttk.Frame(win);edit.pack(fill="x")
    observed=tk.BooleanVar();morph=tk.StringVar();notes=tk.StringVar()
    ttk.Checkbutton(edit,text="Observed in game",variable=observed).pack(side="left")
    ttk.Entry(edit,textvariable=morph,width=22).pack(side="left")
    ttk.Entry(edit,textvariable=notes,width=28).pack(side="left")
    weights=ttk.Treeview(win,columns=("phoneme","slot","weight"),show="headings",height=7)
    for c in ("phoneme","slot","weight"):weights.heading(c,text=c.title())
    weights.pack(fill="both",expand=True)
    inputs=ttk.Frame(win);inputs.pack(fill="x")
    ph=tk.StringVar();slot=tk.StringVar();weight=tk.StringVar(value="0.5")
    for label,v in (("Phoneme",ph),("Slot",slot),("Weight",weight)):
        ttk.Label(inputs,text=label).pack(side="left");ttk.Entry(inputs,textvariable=v,width=12).pack(side="left")
    def guard(fn):
        def run(*_):
            try:fn()
            except Exception as exc:messagebox.showerror("Morph profile",str(exc),parent=win)
        return run
    def redraw():
        p=state["profile"]
        slots.delete(*slots.get_children());weights.delete(*weights.get_children())
        for s,row in sorted(p["observations"].items(),key=lambda x:int(x[0])):
            slots.insert("","end",iid=s,text=s,values=(row["observed"],row["morph"],row.get("notes","")))
        for name,items in sorted(p.get("phonemes",{}).items()):
            for s,w in items.items():weights.insert("","end",values=(name,s,w))
    def commit(p):
        state["profile"]=mc.profile(p);redraw()
    def selected():
        if slots.selection():
            s=slots.selection()[0];r=state["profile"]["observations"][s]
            observed.set(r["observed"]);morph.set(r["morph"]);notes.set(r.get("notes",""));slot.set(s)
    def apply():
        if not slots.selection():raise ValueError("Select a slot")
        p=copy.deepcopy(state["profile"]);p["observations"][slots.selection()[0]]={"observed":observed.get(),"morph":morph.get(),"notes":notes.get()}
        commit(p)
    def map_weight(remove=False):
        p=copy.deepcopy(state["profile"]);name=ph.get().strip();s=slot.get().strip()
        if not name or name=="sil":raise ValueError("Choose a non-silence phoneme")
        m=p.setdefault("phonemes",{})
        if remove:
            if name not in m or s not in m[name]:raise ValueError("Mapping missing")
            del m[name][s]
            if not m[name]:del m[name]
        else:m.setdefault(name,{})[s]=float(weight.get())
        commit(p)
    def pick_weight():
        if weights.selection():
            a,b,c=weights.item(weights.selection()[0],"values");ph.set(a);slot.set(b);weight.set(c)
    def load():
        p=filedialog.askopenfilename(parent=win,filetypes=[("Profile JSON","*.json")])
        if p:commit(json.loads(Path(p).read_text(encoding="utf-8")))
    def save():
        p=filedialog.asksaveasfilename(parent=win,defaultextension=".json")
        if p:audio.publish(Path(p),json.dumps(mc.profile(state["profile"]),ensure_ascii=False,indent=2).encode("utf-8"))
    def new():
        if messagebox.askyesno("New profile","Discard current edits?",parent=win):commit(empty())
    for label,fn in (("New",new),("Load",load),("Save new profile",save)):
        ttk.Button(bar,text=label,command=guard(fn)).pack(side="left")
    ttk.Button(edit,text="Apply observation",command=guard(apply)).pack(side="left")
    ttk.Button(inputs,text="Set weight",command=guard(map_weight)).pack(side="left")
    ttk.Button(inputs,text="Remove weight",command=guard(lambda:map_weight(True))).pack(side="left")
    slots.bind("<<TreeviewSelect>>",guard(selected));weights.bind("<<TreeviewSelect>>",guard(pick_weight))
    redraw()
