"""Unified Asset Forge desktop workbench using existing model generators."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from . import rock_gen,flora,architecture
from .asset_forge import Session
from .scene import load_obj,Scene,Instance,Camera,frame,project
from .lod import bounds

def mount(parent):
    sources={"Rock":(rock_gen.RockRecipe,rock_gen.generate),
             "Tree / shrub / grass":(flora.Recipe,flora.generate),
             "Modular building":(architecture.Building,lambda r:architecture.generate(r)[0])}
    state={"session":None,"camera":None,"yaw":35,"pitch":32,"zoom":1.0,"orbit":None};fields={}
    mode=tk.StringVar(value="vertex");selected=tk.StringVar(value="")
    gizmo_mode=tk.StringVar(value="select");show_collision=tk.BooleanVar(value=True)
    state.update(handles=[],drag=None)
    controls=ttk.Frame(parent);controls.pack(fill="x")
    source=tk.StringVar(value="Rock")
    ttk.Label(controls,text="Model source").pack(side="left")
    selector=ttk.Combobox(controls,textvariable=source,values=list(sources),state="readonly")
    selector.pack(side="left")
    params=ttk.Frame(parent);params.pack(fill="x")
    def parameters(event=None):
        for child in params.winfo_children():child.destroy()
        fields.clear()
        recipe=sources[source.get()][0]()
        for i,(name,value) in enumerate(vars(recipe).items()):
            ttk.Label(params,text=name.capitalize()).grid(row=i//4*2,column=i%4,sticky="w")
            v=tk.StringVar(value=str(value));fields[name]=v
            if name=="species":
                ttk.Combobox(params,textvariable=v,values=["tree","shrub","grass"],state="readonly",width=14).grid(row=i//4*2+1,column=i%4)
            else:ttk.Entry(params,textvariable=v,width=14).grid(row=i//4*2+1,column=i%4)
    selector.bind("<<ComboboxSelected>>",parameters);parameters()
    canvas=tk.Canvas(parent,background="#202631",height=320)
    canvas.pack(fill="both",expand=True)
    status=tk.StringVar(value="Generate a model or import a triangulated OBJ.")
    ttk.Label(parent,textvariable=status,wraplength=850).pack(fill="x")
    def session():
        if state["session"] is None:raise ValueError("Generate or import a model first")
        return state["session"]
    def draw(event=None):
        if state["session"] is None:return
        s=session();m=s.mesh;b=bounds(m);center=tuple((lo+hi)/2 for lo,hi in b)
        span=max(max(hi-lo for lo,hi in b),.001)
        w=max(canvas.winfo_width(),100);h=max(canvas.winfo_height(),100)
        camera=Camera(yaw=state["yaw"],pitch=state["pitch"],center=center,zoom=min(w,h)*.65/span*state["zoom"])
        state["camera"]=(camera,w,h)
        canvas.delete("all");state["handles"]=[]
        for _,_,coords,color in frame(Scene({"mesh":m},[Instance("preview","mesh")]),camera,w,h,budget=6000):
            canvas.create_polygon(*coords,fill=color,outline="#25323d")
        if selected.get().strip():
            try:
                ids=s.selection_vertices(mode.get(),indices())
                for i in sorted(ids)[:2000]:
                    x,y,_=project(m.vertices[i],camera,w,h)
                    canvas.create_oval(x-3,y-3,x+3,y+3,fill="#efc15d",outline="")
                if gizmo_mode.get()!="select":
                    from .asset_gizmo import pivot
                    p=pivot(m,ids);origin=project(p,camera,w,h)
                    for axis,color in enumerate(("#ec6c6c","#70d481","#77a8ff")):
                        unit=list(p);unit[axis]+=1
                        q=project(unit,camera,w,h);dx,dy=q[0]-origin[0],q[1]-origin[1]
                        length=(dx*dx+dy*dy)**.5
                        if length<1e-8:continue
                        end=(origin[0]+55*dx/length,origin[1]+55*dy/length)
                        canvas.create_line(*origin[:2],*end,fill=color,width=3,arrow="last")
                        canvas.create_text(*end,text="XYZ"[axis],fill=color,anchor="sw")
                        state["handles"].append((axis,origin[:2],end,(dx,dy)))
            except ValueError:pass
        if show_collision.get() and s.collision:
            for box in s.collision["boxes"]:
                lo,hi=box["min"],box["max"]
                pts=[project((x,y,z),camera,w,h) for z in (lo[2],hi[2]) for y in (lo[1],hi[1]) for x in (lo[0],hi[0])]
                for i in range(8):
                    for bit in (1,2,4):
                        j=i^bit
                        if i<j:canvas.create_line(*pts[i][:2],*pts[j][:2],fill="#ef8559" if s.collision_stale else "#79dfd5",dash=(4,3))
        status.set(f"{len(m.vertices)} vertices | {len(m.faces)} triangles | {len(s.groups())} material groups | {len(s.materials)} bindings | preview only")
    canvas.bind("<Configure>",draw)
    def replace(mesh):
        candidate=mesh if isinstance(mesh,Session) else Session(mesh)
        if state["session"] is not None and not messagebox.askyesno("Replace asset","Discard the current editing session?"):return
        state["session"]=candidate;selected.set("");draw()
    def generate():
        cls,fn=sources[source.get()]
        values={k:type(v)(fields[k].get()) for k,v in vars(cls()).items()}
        replace(fn(cls(**values)))
    def import_obj(dropped=None):
        path=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Triangulated OBJ","*.obj")])
        if path:replace(load_obj(path))
    def import_nif(dropped=None):
        if not messagebox.askyesno("Import NIF","Import static geometry only? Original shaders, collision, metadata and animation will not be preserved. A rebuilt trusted native helper is required."):return
        path=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Native NIF","*.nif")])
        if not path:return
        helper=filedialog.askopenfilename(title="Select trusted Chimster native helper")
        if helper:
            from .asset_nif_import import import_modern
            replace(import_modern(path,helper))
    def indices():
        return [int(x) for x in selected.get().replace(","," ").split()]
    def pick(event):
        if state["session"] is None or state["camera"] is None:return
        s=session();m=s.mesh;cam,w,h=state["camera"]
        if len(m.faces)>6000 or len(m.vertices)>12000:
            status.set("Click selection is limited to small meshes; enter zero-based indices.");return
        pts=[project(p,cam,w,h) for p in m.vertices];x,y=event.x,event.y
        def dist(p):return (p[0]-x)**2+(p[1]-y)**2
        def segment(a,b):
            dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
            t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/den)) if den else 0
            return dist((a[0]+t*dx,a[1]+t*dy))
        if mode.get()=="vertex":
            i=min(range(len(pts)),key=lambda i:(dist(pts[i]),-pts[i][2]))
            if dist(pts[i])>144:return
        elif mode.get()=="edge":
            edges=s.edges()
            i=min(range(len(edges)),key=lambda i:(segment(*(pts[v] for v in edges[i])),-sum(pts[v][2] for v in edges[i])))
            if segment(*(pts[v] for v in edges[i]))>144:return
        else:
            hits=[]
            for i,(t,_) in enumerate(m.faces):
                a,b,c=[pts[v] for v in t]
                def cross(p,q):return (q[0]-p[0])*(y-p[1])-(q[1]-p[1])*(x-p[0])
                vals=[cross(a,b),cross(b,c),cross(c,a)]
                area=(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
                if abs(area)>1e-9 and (min(vals)>=0 or max(vals)<=0):hits.append((sum(p[2] for p in (a,b,c)),i))
            if not hits:return
            i=max(hits)[1]
        if event.state & 1:
            ids=set(indices());ids.symmetric_difference_update({i});selected.set(" ".join(map(str,sorted(ids))))
        else:selected.set(str(i))
        draw()
    def press(e):
        if gizmo_mode.get()!="select":
            for axis,origin,end,pixels in state["handles"]:
                if (e.x-end[0])**2+(e.y-end[1])**2<=144:
                    op=gizmo_mode.get()
                    if op!="move":pixels=(end[0]-origin[0],end[1]-origin[1])
                    state["drag"]=(session(),mode.get(),indices(),op,axis,(e.x,e.y),pixels);return
        pick(e)
    def drag(e):
        if state["drag"] is not None:
            canvas.delete("gesture")
            start=state["drag"][5]
            canvas.create_line(*start,e.x,e.y,fill="#efc15d",width=2,tags="gesture")
    def release(e):
        data=state["drag"];state["drag"]=None
        canvas.delete("gesture")
        if data is None:return
        s,selection,ids,op,axis,start,pixels=data
        if s is not state["session"] or start==(e.x,e.y):return
        try:
            from .asset_gizmo import gesture
            s.gizmo(selection,ids,op,axis,gesture(op,start,(e.x,e.y),pixels));draw()
        except ValueError as exc:messagebox.showerror("Transform",str(exc))
    canvas.bind("<Button-1>",press);canvas.bind("<B1-Motion>",drag);canvas.bind("<ButtonRelease-1>",release)
    def add_box():
        s=session();name=simpledialog.askstring("Collision box","Unique box ID",initialvalue="box_"+str(len(s.collision["boxes"]) if s.collision else 0))
        if name is None:return
        mat=simpledialog.askstring("Collision material","FO3/FNV material name (e.g. stone, wood, metal)",initialvalue="stone")
        if mat is None:return
        pad=simpledialog.askfloat("Collision","Padding in mesh units",initialvalue=.01,minvalue=0)
        if pad is not None:s.add_collision_box(mode.get(),indices(),name,mat,pad);draw()
    def edit_collision():
        import json
        s=session();win=tk.Toplevel(parent);win.title("Compound collision recipe — review box bounds")
        txt=tk.Text(win,width=70,height=20);txt.pack(fill="both",expand=True)
        txt.insert("1.0",json.dumps(s.collision or {"kind":"compound_aabb","list_material":"stone","boxes":[]},indent=2))
        def apply():
            if s is not state["session"]:raise ValueError("Asset session changed")
            s.set_collision(json.loads(txt.get("1.0","end")));win.destroy();draw()
        ttk.Button(win,text="Validate and approve",command=guard(apply)).pack()
        def clear():
            if s is not state["session"]:raise ValueError("Asset session changed")
            if messagebox.askyesno("Collision","Remove all compound collision boxes?"):
                s.set_collision(None);win.destroy();draw()
        ttk.Button(win,text="Clear collision",command=guard(clear)).pack()

    def orbit_start(e):state["orbit"]=(e.x,e.y)
    def orbit(e):
        if state["orbit"] is None:return
        x,y=state["orbit"];state["orbit"]=(e.x,e.y)
        state["yaw"]=(state["yaw"]+(e.x-x)*.4)%360
        state["pitch"]=max(-85,min(85,state["pitch"]+(e.y-y)*.4));draw()
    def zoom(factor):
        state["zoom"]=max(.2,min(8,state["zoom"]*factor));draw()
    canvas.bind("<ButtonPress-3>",orbit_start);canvas.bind("<B3-Motion>",orbit)
    canvas.bind("<ButtonRelease-3>",lambda e:state.update(orbit=None))
    canvas.bind("<MouseWheel>",lambda e:zoom(1.15 if e.delta>0 else 1/1.15))
    canvas.bind("<Button-4>",lambda e:zoom(1.15));canvas.bind("<Button-5>",lambda e:zoom(1/1.15))
    def extrude():
        if mode.get()!="face":raise ValueError("Select faces")
        val=simpledialog.askstring("Extrude","XYZ extrusion vector",initialvalue="0 0 1")
        if val is not None:
            ids=session().extrude_faces(indices(),tuple(map(float,val.split())))
            selected.set(" ".join(map(str,ids)));draw()
    def weld():
        if mode.get()!="vertex":raise ValueError("Select vertices")
        val=simpledialog.askfloat("Weld","Maximum distance from lowest selected vertex; identical UV/material membership required",initialvalue=.001,minvalue=0,maxvalue=1e6)
        if val is not None and messagebox.askyesno("Weld","Merge selected vertices and remove collapsed triangles?"):
            session().weld_vertices(indices(),val);selected.set("");draw()
    def uv_project():
        if mode.get()!="face":raise ValueError("Select faces")
        val=simpledialog.askstring("Planar UV","Projection plane: XY, XZ, YZ",initialvalue="XY")
        if val is not None:session().project_uv(indices(),val.strip().upper());draw()
    def uv_transform():
        val=simpledialog.askstring("UV transform","U scale, V scale, U offset, V offset (space-separated)",initialvalue="1 1 0 0")
        if val is not None:
            a,b,c,d=map(float,val.split());session().transform_uv(mode.get(),indices(),(a,b),(c,d));draw()
    def uv_view():
        s=session();m=s.mesh;ids=set(indices());s.selection_vertices(mode.get(),ids)
        verts=s.selection_vertices(mode.get(),ids)
        win=tk.Toplevel(parent);win.title("UV layout (read-only preview)")
        cv=tk.Canvas(win,width=440,height=440,background="#202631");cv.pack()
        cv.create_rectangle(20,20,420,420,outline="#8293a1")
        def uv(i):
            u,v=m.uv[i];return 20+400*u,420-400*v
        step=max(1,(len(m.faces)+5999)//6000)
        for t,_ in m.faces[::step]:
            cv.create_polygon(*(a for i in t for a in uv(i)),fill="",outline="#efc15d" if set(t)<=verts else "#637889")
    def redo():
        session().redo();selected.set("");draw()
    def move_selected():
        vals=simpledialog.askstring("Move selection","X Y Z displacement",initialvalue="0 0 0")
        if vals is not None:session().move_selection(mode.get(),indices(),tuple(map(float,vals.split())));draw()
    def split_selected():
        ids=indices()
        if mode.get()!="edge" or len(ids)!=1:raise ValueError("Select one edge")
        session().split_edge(ids[0]);selected.set("");draw()
    def delete_selected():
        if mode.get()!="face":raise ValueError("Select faces")
        if messagebox.askyesno("Delete","Delete selected faces?"):
            session().delete_faces(indices());selected.set("");draw()
    def assign_selected():
        if mode.get()!="face":raise ValueError("Select faces")
        group=simpledialog.askstring("Assign material","Exact material group: "+", ".join(session().groups()))
        if group is not None:session().assign_faces(indices(),group);draw()
    def transform():
        s=session()
        scale=simpledialog.askfloat("Transform","Uniform scale",initialvalue=1,minvalue=.000001,maxvalue=100000)
        if scale is None:return
        yaw=simpledialog.askfloat("Transform","Z-axis rotation in degrees",initialvalue=0)
        if yaw is None:return
        ground=messagebox.askyesno("Transform","Move lowest vertex to Z=0?")
        s.transform(scale,yaw,ground);draw()
    def material():
        s=session()
        group=simpledialog.askstring("Material","Choose exact group: "+", ".join(s.groups()))
        if group is None:return
        if group not in s.groups():raise ValueError("Unknown material group")
        old=s.materials.get(group,{})
        diffuse=simpledialog.askstring("Material","Diffuse DDS path relative to game data (blank = none)",initialvalue=old.get("diffuse",""))
        if diffuse is None:return
        normal=simpledialog.askstring("Material","Normal DDS path (blank = none)",initialvalue=old.get("normal",""))
        if normal is None:return
        cut=messagebox.askyesno("Material","Enable alpha cutout?")
        s.bind(group,diffuse,normal,cut);draw()
    def simplify():
        s=session()
        cell=simpledialog.askfloat("LOD","Vertex clustering cell size in mesh units",minvalue=.000001)
        if cell is not None:s.simplify(cell);selected.set("");draw()
    def undo():
        session().undo();selected.set("");draw()
    def save_project():
        s=session();p=filedialog.asksaveasfilename(defaultextension=".casset",filetypes=[("Asset project","*.casset")])
        if p:
            from .asset_project import save
            save(s,p);status.set("Saved editable asset: "+p)
    def open_project(dropped=None):
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Asset project","*.casset")])
        if p:
            from .asset_project import load
            replace(load(p))
    def export_obj():
        s=session();path=filedialog.asksaveasfilename(defaultextension=".obj",filetypes=[("Wavefront OBJ","*.obj")])
        if path:s.export_obj(path);status.set("Exported intermediate geometry: "+path)
    def export_nif():
        s=session()
        game=simpledialog.askstring("Native export","Target: morrowind, openmw, fallout3, newvegas, skyrim, skyrimse, skyrimvr, fallout4, fallout4vr")
        if game is None:return
        game=game.strip().lower()
        from .modern_nif import GAMES
        if game not in GAMES|{"morrowind","openmw"}:raise ValueError("Unsupported native target")
        scale=simpledialog.askfloat("Native export","Mesh-to-game unit scale",minvalue=.000001,maxvalue=100000,initialvalue=1)
        if scale is None:return
        helper=None
        if game in GAMES:
            if not messagebox.askyesno("Native helper","Only choose a trusted, locally built Chimster NIF helper. Continue?"):return
            helper=filedialog.askopenfilename(title="Select trusted native NIF helper")
            if not helper:return
        compound=game in {"fallout3","newvegas"} and s.collision is not None and messagebox.askyesno("Collision","Export authored compound collision boxes?")
        box=not compound and game in {"fallout3","newvegas"} and messagebox.askyesno("Collision","Include experimental solid bounding-box collision? Not suitable for walkable interiors.")
        path=filedialog.asksaveasfilename(defaultextension=".nif",filetypes=[("Native NIF","*.nif")])
        if path:
            report=s.export_nif(path,game,scale,helper,box,compound)
            status.set(str(report.get("status","Native export completed; runtime unverified")))
    def guard(fn):
        def run():
            try:fn()
            except (ValueError,OSError,OverflowError,RuntimeError,ImportError,KeyError) as e:messagebox.showerror("Asset Forge",str(e))
        return run
    editbar=ttk.Frame(parent);editbar.pack(fill="x")
    ttk.Label(editbar,text="Selection (zero-based)").pack(side="left")
    pickmode=ttk.Combobox(editbar,textvariable=mode,values=["vertex","edge","face"],state="readonly",width=8);pickmode.pack(side="left")
    pickmode.bind("<<ComboboxSelected>>",lambda e:(selected.set(""),draw()))
    entry=ttk.Entry(editbar,textvariable=selected,width=20);entry.pack(side="left");entry.bind("<Return>",draw)
    for label,fn in (("Move",move_selected),("Split edge",split_selected),("Delete faces",delete_selected),("Assign faces",assign_selected)):
        ttk.Button(editbar,text=label,command=guard(fn)).pack(side="left")
    gbar=ttk.Frame(parent);gbar.pack(fill="x")
    ttk.Label(gbar,text="Gizmo").pack(side="left")
    g=ttk.Combobox(gbar,textvariable=gizmo_mode,values=["select","move","rotate","scale"],state="readonly",width=8);g.pack(side="left")
    g.bind("<<ComboboxSelected>>",draw)
    ttk.Checkbutton(gbar,text="Collision overlay",variable=show_collision,command=draw).pack(side="left")
    ttk.Button(gbar,text="Box from selection",command=guard(add_box)).pack(side="left")
    ttk.Button(gbar,text="Edit/review boxes",command=guard(edit_collision)).pack(side="left")
    more=ttk.Frame(parent);more.pack(fill="x")
    for label,fn in (("Extrude",extrude),("Weld",weld),("Planar UV",uv_project),("UV transform",uv_transform),("UV view",uv_view),("Redo",redo)):
        ttk.Button(more,text=label,command=guard(fn)).pack(side="left")
    ttk.Label(more,text="Shift-click multi-select; right-drag orbit; wheel zoom").pack(side="left")
    for actions in ((("Generate preview",generate),("Import OBJ",import_obj),("Import NIF",import_nif),("Transform",transform),("Material binding",material)),
                    (("Open asset",open_project),("Save new asset",save_project),("Simplify LOD",simplify),("Undo",undo),("Export OBJ",export_obj),("Export NIF",export_nif))):
        bar=ttk.Frame(parent);bar.pack(fill="x")
        for label,fn in actions:ttk.Button(bar,text=label,command=guard(fn)).pack(side="left")
    from .drop_import import editor_drop
    editor_drop(parent,[([".obj"],import_obj,False),([".nif"],import_nif,False),([".casset"],open_project,False)])
