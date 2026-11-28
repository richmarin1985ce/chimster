"""Experimental raw facial curve editing; slot names are intentionally unknown."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from . import lip_curves as lc
from .audio import publish

def launch(parent):
    win=tk.Toplevel(parent);win.title("Chimster — Native facial curves (experimental)");win.geometry("820x590")
    state={"data":None,"meta":None,"cells":[],"changes":{}}
    bar=ttk.Frame(win);bar.pack(fill="x")
    slot=tk.StringVar();slots=ttk.Combobox(bar,textvariable=slot,state="readonly",width=9);slots.pack(side="left")
    canvas=tk.Canvas(win,height=220,bg="#20252c");canvas.pack(fill="x",padx=8,pady=6)
    table=ttk.Treeview(win,columns=("frame","value","type"),show="headings",height=10)
    for col in ("frame","value","type"):table.heading(col,text=col)
    table.pack(fill="both",expand=True,padx=8)
    entry=ttk.Entry(win);entry.pack(anchor="w")
    status=tk.StringVar(value="Open native LIP. Raw slots are not calibrated mouth morphs.")
    ttk.Label(win,textvariable=status).pack(anchor="w")
    def guard(fn):
        def run(*_):
            try:fn()
            except Exception as e:messagebox.showerror("Native curves",str(e),parent=win)
        return run
    def selected_cells():
        return [c for c in state["cells"] if str(c["curve"])==slot.get()]
    def value(c):
        return state["changes"].get((c["frame"],c["curve"]),c["value"])
    def draw(*_):
        canvas.delete("all")
        cells=selected_cells()
        if not cells:return
        w=max(1,canvas.winfo_width()-24);h=max(1,canvas.winfo_height()-24)
        low=min(0,min(value(c) for c in cells));high=max(1,max(value(c) for c in cells))
        frames=max(1,state["meta"]["frames"]-1)
        pts=[]
        for c in cells:
            x=12+w*c["frame"]/frames;y=12+h*(high-value(c))/(high-low)
            pts.extend((x,y))
        if len(pts)>=4:canvas.create_line(*pts,fill="#97c9d3",width=2)
        for x,y in zip(pts[::2],pts[1::2]):canvas.create_oval(x-2,y-2,x+2,y+2,fill="#97c9d3",outline="")
    def refresh(*_):
        table.delete(*table.get_children())
        for c in selected_cells():
            table.insert("","end",iid=str(c["frame"]),values=(c["frame"],format(value(c),".8g"),"pair (read-only)" if c["dup"] else "raw"))
        draw()
    def open_file(dropped=None):
        p=dropped if dropped is not None else filedialog.askopenfilename(parent=win,filetypes=[("Native LIP","*.lip")])
        if not p:return
        data=lc.read(p);meta,cells,_=lc.decode(data)
        state.update(data=data,meta=meta,cells=cells,changes={})
        options=sorted({c["curve"] for c in cells});slots.configure(values=options);slot.set(str(options[0]));refresh()
        status.set(meta["game"]+" — byte-exact structural roundtrip; runtime unverified")
    def selected(*_):
        s=table.selection()
        if s:entry.delete(0,"end");entry.insert(0,table.item(s[0],"values")[1])
    def edits(changes):
        return [{"frame":f,"slot":s,"value":v} for (f,s),v in sorted(changes.items())]
    def apply():
        if not table.selection():raise ValueError("Select an existing key")
        key=(int(table.selection()[0]),int(slot.get()))
        changes=dict(state["changes"]);changes[key]=float(entry.get())
        lc.edit(state["data"],edits(changes),experimental=True)
        state["changes"]=changes;refresh()
        status.set("Staged "+str(len(changes))+" experimental edits")
    def save():
        if not state["changes"]:raise ValueError("No edits staged")
        if not messagebox.askyesno("Experimental output","Save an unverified Skyrim LIP? Test in-game before release.",parent=win):return
        p=filedialog.asksaveasfilename(parent=win,defaultextension=".lip")
        if p:
            if Path(p).suffix.lower()!=".lip":raise ValueError("Choose .lip")
            publish(Path(p),lc.edit(state["data"],edits(state["changes"]),experimental=True))
            status.set("Saved new experimental LIP")
    def csv_export():
        if state["data"] is None:raise ValueError("Open LIP")
        p=filedialog.asksaveasfilename(parent=win,defaultextension=".csv")
        if p:
            data=lc.edit(state["data"],edits(state["changes"]),experimental=True) if state["changes"] else state["data"]
            publish(Path(p),lc.export_csv(data).encode("utf-8"))
    for label,fn in (("Open LIP",open_file),("Apply raw weight",apply),("Save new LIP",save),("Export CSV",csv_export)):
        ttk.Button(bar,text=label,command=guard(fn)).pack(side="left")
    slots.bind("<<ComboboxSelected>>",refresh);table.bind("<<TreeviewSelect>>",selected);canvas.bind("<Configure>",draw)
    from .drop_import import editor_drop
    editor_drop(win,[([".lip"],open_file,False)])
