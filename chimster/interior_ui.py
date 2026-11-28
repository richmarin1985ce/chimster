"""Top-down interior workbench; project JSON remains the source of native export."""
import json, tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from .interior_edit import History,cell,make_portal
from .interior_layout import validate

EXAMPLE={"schema":1,"cells":[{"id":"Interior","title":"Interior","layout":{"schema":1,
    "rooms":[{"id":"A","min":[0,0,0],"max":[4,4,4]},{"id":"B","min":[4,0,0],"max":[8,4,4]}],"portals":[]},"placements":[]}]}

def mount(parent):
    h=History(EXAMPLE);active=tk.StringVar(value="Interior");status=tk.StringVar()
    bar=ttk.Frame(parent);bar.pack(fill="x")
    combo=ttk.Combobox(bar,textvariable=active,state="readonly",width=18);combo.pack(side="left")
    panes=ttk.Panedwindow(parent,orient="horizontal");panes.pack(fill="both",expand=True)
    canvas=tk.Canvas(panes,bg="#202832",width=480,height=400);panes.add(canvas,weight=3)
    right=ttk.Frame(panes);panes.add(right,weight=2)
    tree=ttk.Treeview(right,show="tree",height=10);tree.pack(fill="both",expand=True)
    props=tk.Text(right,height=12,wrap="none");props.pack(fill="both",expand=True)
    ttk.Label(parent,textvariable=status,wraplength=800).pack(fill="x")
    rows={};selection=None;transform=None
    def guard(fn):
        try:fn()
        except (ValueError,KeyError,TypeError,OSError,tk.TclError) as exc:messagebox.showerror("Interior",str(exc))
    def current():return cell(h.current,active.get())
    def select(key):
        nonlocal selection
        if key not in rows:return
        selection=key
        if tree.selection()!=(key,):tree.selection_set(key)
        props.delete("1.0","end");props.insert("1.0",json.dumps(rows[key][1],indent=2))
    def draw(*_):
        nonlocal transform
        combo.configure(values=[c["id"] for c in h.current["cells"]])
        if active.get() not in combo["values"]:active.set(combo["values"][0])
        c=current();layout=c.get("layout",{"schema":1,"rooms":[]})
        old=selection;tree.delete(*tree.get_children());rows.clear();canvas.delete("all")
        objects=[(k,r) for k in ("room","portal","trigger","node") for r in layout.get(k+"s",[])]
        objects += [("placement",p) for p in c.get("placements",[])]
        points=[p for k,r in objects for p in ([r["min"],r["max"]] if k in ("room","trigger") else r["corners"] if k=="portal" else [r["position"]])]
        if points:
            lo=[min(p[i] for p in points) for i in (0,1)];hi=[max(p[i] for p in points) for i in (0,1)]
        else:lo=[0,0];hi=[8,8]
        w=max(canvas.winfo_width(),100);height=max(canvas.winfo_height(),100)
        scale=min((w-40)/max(hi[0]-lo[0],1),(height-40)/max(hi[1]-lo[1],1))
        transform=(lo,scale,height)
        def xy(p):return (20+(p[0]-lo[0])*scale,height-20-(p[1]-lo[1])*scale)
        for k,r in objects:
            key=k+":"+r["id"];rows[key]=(k,r);tree.insert("","end",iid=key,text=k+" / "+r["id"])
            tags=(key,)
            if k in ("room","trigger"):
                a,b=xy(r["min"]),xy(r["max"])
                canvas.create_rectangle(a[0],b[1],b[0],a[1],fill="#344d60" if k=="room" else "",outline="#8daec6" if k=="room" else "#e8b361",width=2,tags=tags)
                canvas.create_text((a[0]+b[0])/2,(a[1]+b[1])/2,text=r["id"],fill="white",tags=tags)
            elif k=="portal":
                ps=[xy(p) for p in r["corners"]];a,b=max(((a,b) for a in ps for b in ps),key=lambda ab:(ab[0][0]-ab[1][0])**2+(ab[0][1]-ab[1][1])**2)
                canvas.create_line(*a,*b,fill="#73e3a2",width=5,tags=tags)
            else:
                x,y=xy(r["position"]);canvas.create_oval(x-5,y-5,x+5,y+5,fill="#ffc56c",tags=tags)
                canvas.create_text(x,y-12,text=r["id"],fill="white",tags=tags)
        if old in rows:select(old)
        else:props.delete("1.0","end")
        report=validate(layout);status.set(f"{len(layout.get('rooms',[]))} rooms | {len(layout.get('portals',[]))} portals | {len(c.get('placements',[]))} placements | "+("layout valid" if report["valid"] else str(report["issues"])))
    def apply():
        if selection not in rows:raise ValueError("select an object")
        k,r=rows[selection];updated=json.loads(props.get("1.0","end-1c"))
        if updated["id"]!=r["id"]:raise ValueError("ID changes require explicit reference migration")
        h.edit(active.get(),k,updated);draw()
    def add_room():
        name=simpledialog.askstring("Room","Unique room ID")
        if name:
            raw=simpledialog.askstring("Room bounds","Six values: min x y z, max x y z",initialvalue="8 0 0 12 4 4")
            if raw:
                values=list(map(float,raw.split()))
                if len(values)!=6:raise ValueError("six coordinates required")
                h.edit(active.get(),"room",{"id":name,"min":values[:3],"max":values[3:]});draw()
    def add_portal():
        raw=simpledialog.askstring("Portal","Portal ID, room A, room B (space separated)")
        if raw:
            name,a,b=raw.split();h.edit(active.get(),"portal",make_portal(current()["layout"],name,a,b));draw()
    def add_placement():
        raw=simpledialog.askstring("Placement","Placement ID, base ID, x, y, z")
        if raw:
            name,base,x,y,z=raw.split();h.edit(active.get(),"placement",{"id":name,"base":base,"position":[float(x),float(y),float(z)]});draw()
    def bind():
        raw=simpledialog.askstring("Bind portal","Portal ID and placed door ID")
        if raw:
            p,d=raw.split();h.bind(active.get(),p,d);draw()
    def open_project():
        p=filedialog.askopenfilename(filetypes=[("Interior project","*.json")])
        if p:
            path=Path(p)
            if path.stat().st_size>32*1024*1024:raise ValueError("project too large")
            h.commit(json.loads(path.read_text(encoding="utf-8")));draw()
    def save():
        p=filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            with Path(p).open("x",encoding="utf-8") as f:json.dump(h.current,f,indent=2)
    def diagnose():
        from .interior_diagnostics import audit
        report=audit(h.current)
        win=tk.Toplevel(parent);win.title("Connectivity diagnostics")
        out=tk.Text(win,width=85,height=28,wrap="word");out.pack(fill="both",expand=True);out.insert("1.0",json.dumps(report,indent=2));out.configure(state="disabled")
    def export():
        from .fnv_interior import export as native
        path=filedialog.asksaveasfilename(defaultextension=".esp")
        if not path:return
        masters=filedialog.askopenfilenames(title="Optional masters in load order")
        result=native(h.current,path,masters)
        status.set(json.dumps(result))
    for label,fn in (("Open",open_project),("Save new",save),("Room",add_room),("Portal",add_portal),("Place",add_placement),("Bind door",bind),("Apply properties",apply),("Undo",lambda:(h.undo(),draw())),("Redo",lambda:(h.redo(),draw())),("Diagnostics",diagnose),("Export FNV",export)):
        ttk.Button(bar,text=label,command=lambda fn=fn:guard(fn)).pack(side="left")
    def pick(e):
        items=canvas.find_overlapping(e.x-3,e.y-3,e.x+3,e.y+3)
        for item in reversed(items):
            tags=canvas.gettags(item)
            if tags and tags[0] in rows:select(tags[0]);break
    def on_tree(_):
        if tree.selection():select(tree.selection()[0])
    canvas.bind("<Button-1>",pick);tree.bind("<<TreeviewSelect>>",on_tree)
    combo.bind("<<ComboboxSelected>>",draw);canvas.bind("<Configure>",draw);draw()
