"""Unified Asset Forge desktop workbench using existing model generators."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from . import rock_gen,flora,architecture
from .asset_forge import Session
from .scene import load_obj,Scene,Instance,Camera,frame
from .lod import bounds

def mount(parent):
    sources={"Rock":(rock_gen.RockRecipe,rock_gen.generate),
             "Tree / shrub / grass":(flora.Recipe,flora.generate),
             "Modular building":(architecture.Building,lambda r:architecture.generate(r)[0])}
    state={"session":None};fields={}
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
        camera=Camera(center=center,zoom=min(w,h)*.65/span)
        canvas.delete("all")
        for _,_,coords,color in frame(Scene({"mesh":m},[Instance("preview","mesh")]),camera,w,h,budget=6000):
            canvas.create_polygon(*coords,fill=color,outline="#25323d")
        status.set(f"{len(m.vertices)} vertices | {len(m.faces)} triangles | {len(s.groups())} material groups | {len(s.materials)} bindings | preview only")
    canvas.bind("<Configure>",draw)
    def replace(mesh):
        candidate=Session(mesh)
        if state["session"] is not None and not messagebox.askyesno("Replace asset","Discard the current editing session?"):return
        state["session"]=candidate;draw()
    def generate():
        cls,fn=sources[source.get()]
        values={k:type(v)(fields[k].get()) for k,v in vars(cls()).items()}
        replace(fn(cls(**values)))
    def import_obj():
        path=filedialog.askopenfilename(filetypes=[("Triangulated OBJ","*.obj")])
        if path:replace(load_obj(path))
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
        if cell is not None:s.simplify(cell);draw()
    def undo():
        session().undo();draw()
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
        box=game in {"fallout3","newvegas"} and messagebox.askyesno("Collision","Include experimental solid bounding-box collision? Not suitable for walkable interiors.")
        path=filedialog.asksaveasfilename(defaultextension=".nif",filetypes=[("Native NIF","*.nif")])
        if path:
            report=s.export_nif(path,game,scale,helper,box)
            status.set(str(report.get("status","Native export completed; runtime unverified")))
    def guard(fn):
        def run():
            try:fn()
            except (ValueError,OSError,OverflowError,RuntimeError,ImportError,KeyError) as e:messagebox.showerror("Asset Forge",str(e))
        return run
    for actions in ((("Generate preview",generate),("Import OBJ",import_obj),("Transform",transform),("Material binding",material)),
                    (("Simplify LOD",simplify),("Undo",undo),("Export OBJ",export_obj),("Export NIF",export_nif))):
        bar=ttk.Frame(parent);bar.pack(fill="x")
        for label,fn in actions:ttk.Button(bar,text=label,command=guard(fn)).pack(side="left")
