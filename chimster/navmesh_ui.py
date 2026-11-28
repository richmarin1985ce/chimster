"""Visual portable navmesh authoring and route review."""
import json,tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .navmesh import generate,quality,route,remove_triangles
from .navmesh_rooms import build

def mount(parent):
    bar=ttk.Frame(parent);bar.pack(fill="x")
    pane=ttk.Panedwindow(parent,orient="horizontal");pane.pack(fill="both",expand=True)
    editor=tk.Text(pane,wrap="none",width=40);pane.add(editor,weight=1)
    canvas=tk.Canvas(pane,bg="#202832");pane.add(canvas,weight=3)
    editor.insert("1.0",json.dumps({"schema":1,"origin":[0,0,0],"spacing":1,
        "heights":[[0]*11 for _ in range(11)],"agent":{"radius":.3,"height":1.8,"max_slope":45,"max_step":.4}},indent=2))
    status=tk.StringVar(value="Load a heightfield, room layout or collision triangle source, then generate.")
    ttk.Label(parent,textvariable=status,wraplength=900).pack(fill="x")
    mesh=None;past=[];selected=[];corridor=set();closed=set();tile_cache=None
    elevation=tk.StringVar(value="All")
    tiled=tk.BooleanVar(value=False)
    ttk.Checkbutton(bar,text="Incremental tiles",variable=tiled).pack(side="left")
    mode=tk.BooleanVar(value=False);spacing=tk.DoubleVar(value=.5);radius=tk.DoubleVar(value=.3);height=tk.DoubleVar(value=1.8)
    ttk.Checkbutton(bar,text="Room layout",variable=mode).pack(side="left")
    for label,var in (("Spacing",spacing),("Radius",radius),("Height",height)):
        ttk.Label(bar,text=label).pack(side="left");ttk.Entry(bar,width=5,textvariable=var).pack(side="left")
    ttk.Label(bar,text="Layer").pack(side="left")
    layer_select=ttk.Combobox(bar,textvariable=elevation,values=("All",),state="readonly",width=7);layer_select.pack(side="left")
    def guard(fn):
        try:fn()
        except (ValueError,KeyError,TypeError,OSError,tk.TclError) as e:messagebox.showerror("Navmesh",str(e))
    def draw(*_):
        canvas.delete("all")
        if mesh is None:return
        vs=mesh["vertices"];ts=mesh["triangles"]
        if not ts:status.set("No walkable triangles; review clearance and input.");return
        if len(ts)>25000:status.set("Mesh exceeds interactive preview limit; save for offline review or use coarser spacing.");return
        used={v for t in ts for v in t};lo=[min(vs[j][i] for j in used) for i in (0,1)]
        hi=[max(vs[j][i] for j in used) for i in (0,1)]
        h=max(canvas.winfo_height(),60);w=max(canvas.winfo_width(),60)
        s=min((w-24)/max(hi[0]-lo[0],.001),(h-24)/max(hi[1]-lo[1],.001))
        def xy(p):return 12+(p[0]-lo[0])*s,h-12-(p[1]-lo[1])*s
        layers=mesh.get("triangle_layers")
        layer_select.configure(values=("All",)+tuple(str(i) for i in sorted(set(layers or []))))
        if elevation.get() not in layer_select["values"]:elevation.set("All")
        labels=mesh.get("triangle_areas",["ground"]*len(ts))
        colors={"ground":"#426b58","ramp":"#536da1","steep":"#927a48","stair":"#9268a2"}
        for i,t in enumerate(ts):
            if layers is not None and elevation.get()!="All" and layers[i]!=int(elevation.get()):continue
            coords=[v for j in t for v in xy(vs[j])]
            canvas.create_polygon(*coords,fill="#eab65b" if i in selected else "#48a7c2" if i in corridor else colors.get(labels[i],"#65727e"),outline="#233a34",tags=(f"tri:{i}",))
        for link in mesh.get("links",[]):
            def center(i):return [sum(vs[j][k] for j in ts[i])/3 for k in range(3)]
            canvas.create_line(*xy(center(link["from"])),*xy(center(link["to"])),fill="#f49b68" if link["id"] in closed else "#d8e6fb",width=2,dash=(4,3))
        status.set(f"{len(ts)} triangles | {len(mesh['regions'])} surface islands | {len(mesh.get('links',[]))} transitions | selected {selected}")
    def auto():
        nonlocal mesh,tile_cache
        spec=json.loads(editor.get("1.0","end-1c"))
        if "vertices" in spec and "triangles" in spec:
            from .navmesh_collision import generate_collision
            if tiled.get():
                from .navmesh_tiles import build as build_tiles
                bundle=build_tiles(spec,tile_cache)
                candidate=bundle["mesh"];tile_cache=bundle["cache"]
            else:candidate=generate_collision(spec)
        else:candidate=build(spec,spacing.get(),{"radius":radius.get(),"height":height.get()}) if mode.get() else generate(spec)
        if mesh is not None:past.append(mesh);past[:]=past[-5:]
        mesh=candidate;selected.clear();corridor.clear();closed.clear();draw()
        if tiled.get() and "vertices" in spec and "triangles" in spec:status.set(f"{len(bundle['rebuilt'])} tiles rebuilt | {len(bundle['reused'])} reused | {mesh['seam_edges']} verified seam edges | {len(mesh['triangles'])} triangles")
    def pick(e):
        items=canvas.find_overlapping(e.x,e.y,e.x,e.y)
        for item in reversed(items):
            tags=canvas.gettags(item)
            if tags and tags[0].startswith("tri:"):
                i=int(tags[0][4:])
                if i in selected:selected.remove(i)
                else:selected.append(i);selected[:]=selected[-2:]
                corridor.clear();draw();break
    def path():
        if mesh is None or len(selected)!=2:raise ValueError("select two triangles")
        report=route(mesh,*selected,mesh.get("links",[]),closed)
        corridor.clear();corridor.update(report["triangles"]);draw()
        status.set("Route found: "+str(len(corridor))+" triangles" if report["reachable"] else "No route")
    def areas():
        nonlocal mesh
        if mesh is None:raise ValueError("generate first")
        from .navmesh_areas import classify
        updated=classify(mesh);past.append(mesh);past[:]=past[-5:]
        mesh=updated;selected.clear();corridor.clear();draw();status.set(str(mesh["area_report"]))
    def simplify_mesh():
        nonlocal mesh
        if mesh is None:raise ValueError("generate first")
        from .navmesh_simplify import simplify
        updated=simplify(mesh);past.append(mesh);past[:]=past[-5:]
        mesh=updated;selected.clear();corridor.clear();draw()
        status.set(str(mesh["simplification"]))
    def exclude():
        nonlocal mesh
        if mesh is None or not selected:raise ValueError("select triangles")
        updated=remove_triangles(mesh,selected);past.append(mesh);past[:]=past[-5:]
        mesh=updated;selected.clear();corridor.clear();draw()
    def undo():
        nonlocal mesh
        if past:mesh=past.pop();selected.clear();corridor.clear();closed.clear();draw()
    def review():
        if mesh is None:raise ValueError("generate first")
        win=tk.Toplevel(parent);win.title("Navmesh quality")
        out=tk.Text(win,width=75,height=25);out.pack(fill="both",expand=True);out.insert("1.0",json.dumps(quality(mesh),indent=2));out.configure(state="disabled")
    def links():
        if mesh is None:raise ValueError("generate first")
        win=tk.Toplevel(parent);win.title("Portal transition state")
        for link in mesh.get("links",[]):
            name=link["id"];v=tk.BooleanVar(win,value=name not in closed)
            def toggle(name=name,v=v):
                if v.get():closed.discard(name)
                else:closed.add(name)
                corridor.clear();draw()
            ttk.Checkbutton(win,text=name,variable=v,command=toggle).pack(anchor="w")
    def load(dropped=None):
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Navigation source JSON","*.json")])
        if p:
            src=Path(p)
            if src.stat().st_size>32*1024*1024:raise ValueError("source too large")
            value=json.loads(src.read_text(encoding="utf-8"))
            editor.delete("1.0","end");editor.insert("1.0",json.dumps(value,indent=2));mode.set("rooms" in value)
    def save():
        if mesh is None:raise ValueError("generate first")
        p=filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            with Path(p).open("x",encoding="utf-8") as f:json.dump(mesh,f)
    buttons=ttk.Frame(parent);buttons.pack(fill="x")
    for label,fn in (("Load source",load),("Auto generate",auto),("Route",path),("Portal states",links),("Classify areas",areas),("Simplify",simplify_mesh),("Exclude selected",exclude),("Undo",undo),("Quality",review),("Save mesh",save)):
        ttk.Button(buttons,text=label,command=lambda fn=fn:guard(fn)).pack(side="left")
    layer_select.bind("<<ComboboxSelected>>",draw)
    canvas.bind("<Button-1>",pick);canvas.bind("<Configure>",draw)
    from .drop_import import editor_drop
    editor_drop(parent,[([".json"],load,False)])
