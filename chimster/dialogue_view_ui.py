"""Native CK dialogue diagram viewer with explicit staged position changes."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from .dialogue_views import parse,inspect,remap,slot_mapping
def mount(parent):
    pane=ttk.Panedwindow(parent,orient="horizontal");pane.pack(fill="both",expand=True)
    left=ttk.Frame(pane);pane.add(left,weight=1)
    right=ttk.Frame(pane);pane.add(right,weight=3)
    lst=tk.Listbox(left,exportselection=False);lst.pack(fill="both",expand=True)
    canvas=tk.Canvas(right,background="#242930");canvas.pack(fill="both",expand=True)
    status=tk.StringVar(value="Open an existing Creation Kit DialogueViews XML.");ttk.Label(parent,textvariable=status,wraplength=900).pack(fill="x")
    path=None;report=None;positions={};selection=None
    def draw():
        canvas.delete("all")
        if not report:return
        nodes=report["nodes"]
        b={n["id"]:[*positions.get(n["id"],n["bounds"][:2]),*n["bounds"][2:]] for n in nodes}
        x0=min(v[0] for v in b.values());y0=min(v[1] for v in b.values())
        w=max(v[0]+v[2] for v in b.values())-x0;h=max(v[1]+v[3] for v in b.values())-y0
        scale=min(max(1,canvas.winfo_width()-40)/max(1,w),max(1,canvas.winfo_height()-40)/max(1,h),2)
        def xy(x,y):return 20+(x-x0)*scale,20+(y-y0)*scale
        for n in nodes:
            if n["class"]=="std:ShapeNode":
                v=b[n["id"]];canvas.create_rectangle(*xy(v[0],v[1]),*xy(v[0]+v[2],v[1]+v[3]),outline="#a5a7aa",dash=(3,3))
        for link in report["links"]:
            a,b2=b[link["origin"]],b[link["destination"]]
            canvas.create_line(*xy(a[0]+a[2],a[1]+a[3]/2),*xy(b2[0],b2[1]+b2[3]/2),fill="#7daccb",arrow="last")
        for n in nodes:
            if n["class"]=="std:ShapeNode":continue
            id=n["id"];v=b[id];a,c=xy(v[0],v[1]);d,e=xy(v[0]+v[2],v[1]+v[3])
            canvas.create_rectangle(a,c,d,e,fill="#51677b" if id==selection else "#39444f",outline="#b0c5d7")
            canvas.create_text(a+4,c+4,text=(n["form_id"] or id)+"\n"+n["caption"][:60],fill="white",anchor="nw",width=max(1,d-a-8))
    def select(event=None):
        nonlocal selection
        if lst.curselection():selection=report["nodes"][lst.curselection()[0]]["id"];draw()
    def open_view():
        nonlocal path,report,positions,selection
        p=filedialog.askopenfilename(filetypes=[("Dialogue view","*.xml")])
        if not p:return
        try:
            r=inspect(parse(p));path=Path(p);report=r;positions={};selection=None
            lst.delete(0,"end")
            for n in r["nodes"]:lst.insert("end",f'{n["form_id"] or n["id"]} {n["caption"][:60]}')
            status.set(f'{path.name}: {len(r["nodes"])} nodes, {len(r["links"])} links');draw()
        except (ValueError,OSError) as e:messagebox.showerror("Dialogue view",str(e))
    def move():
        if selection is None:return
        n=next(n for n in report["nodes"] if n["id"]==selection)
        initial=positions.get(selection,n["bounds"][:2])
        x=simpledialog.askfloat("Node position","X",initialvalue=initial[0],minvalue=-1e7,maxvalue=1e7)
        if x is None:return
        y=simpledialog.askfloat("Node position","Y",initialvalue=initial[1],minvalue=-1e7,maxvalue=1e7)
        if y is not None:positions[selection]=[x,y];draw()
    def save():
        if not path:return
        try:
            old=int(path.stem[:2],16);new=simpledialog.askinteger("Full plugin slot","New hexadecimal slot as decimal (0–253)",initialvalue=old,minvalue=0,maxvalue=253)
            if new is None:return
            m=slot_mapping(path,old,new);folder=filedialog.askdirectory(title="Staging DialogueViews folder")
            if not folder:return
            q=Path(folder)/(m[path.stem.upper()]+".xml");remap(path,q,m,positions=positions or None)
            status.set("Saved staged XML: "+str(q))
        except (ValueError,OSError,KeyError) as e:messagebox.showerror("Dialogue view",str(e))
    lst.bind("<<ListboxSelect>>",select);canvas.bind("<Configure>",lambda e:draw())
    bar=ttk.Frame(parent);bar.pack(fill="x")
    for label,fn in (("Open XML",open_view),("Move selected node",move),("Save staged XML",save)):ttk.Button(bar,text=label,command=fn).pack(side="left")
