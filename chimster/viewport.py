"""Tk desktop viewport with an original portable scene model."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from dataclasses import replace
from pathlib import Path
from .scene import Scene,Instance,Camera,frame,demo_scene,load_obj

def mount(parent):
    from .gpu_viewport import Renderer, Settings, make_demo, load_materials
    scene,materials=make_demo();camera=Camera();selected=None;drag=None
    renderer=None;photo=None;render_size=(1,1);settings=Settings();failure=''
    use_gl=tk.BooleanVar(value=False);lod_text=tk.StringVar(value='22,45,90')
    toolbar=ttk.Frame(parent);toolbar.pack(fill="x")
    pane=ttk.Panedwindow(parent,orient="horizontal");pane.pack(fill="both",expand=True)
    canvas=tk.Canvas(pane,bg="#1b232c",highlightthickness=0);pane.add(canvas,weight=4)
    side=ttk.Frame(pane,padding=6);pane.add(side,weight=1)
    objects=tk.Listbox(side,exportselection=False,height=9);objects.pack(fill="both",expand=True)
    values={k:tk.StringVar(value="0") for k in ("x","y","z","yaw","scale")}
    for k,v in values.items():
        row=ttk.Frame(side);row.pack(fill="x")
        ttk.Label(row,text=k,width=7).pack(side="left");ttk.Entry(row,textvariable=v,width=10).pack(side="right")
    status=tk.StringVar();ttk.Label(parent,textvariable=status).pack(fill="x")
    def draw():
        nonlocal renderer,photo,render_size,failure
        canvas.delete("mesh");canvas.delete("gl")
        if use_gl.get() and canvas.winfo_width()>4 and canvas.winfo_height()>4:
            try:
                from PIL import Image,ImageTk
                if renderer is None:renderer=Renderer()
                w,h=canvas.winfo_width(),canvas.winfo_height()
                factor=min(1,1280/w,720/h);rw,rh=max(1,int(w*factor)),max(1,int(h*factor))
                # Keep camera magnification consistent with the canvas.
                scaled=replace(camera,zoom=camera.zoom*factor)
                raw,stats=renderer.render(scene,scaled,rw,rh,materials,settings,selected)
                image=Image.frombytes("RGBA",(rw,rh),raw)
                if (rw,rh)!=(w,h):image=image.resize((w,h),Image.Resampling.BILINEAR)
                photo=ImageTk.PhotoImage(image);render_size=(rw,rh)
                canvas.create_image(0,0,image=photo,anchor="nw",tags=("gl",))
                status.set(f'{stats["renderer"]} | {stats["triangles"]} tris | {stats["draw_calls"]} draws | {stats["culled"]} culled | {stats["frame_ms"]:.1f} ms | LOD {stats["lod_counts"]}')
                return
            except Exception as e:
                failure=str(e)[:180];use_gl.set(False)
                if renderer is not None:
                    try:renderer.close()
                    except Exception:pass
                    renderer=None
        canvas.delete("gl")
        rows=frame(scene,camera,max(1,canvas.winfo_width()),max(1,canvas.winfo_height()))
        for _,id,coords,color in rows:
            canvas.create_polygon(*coords,fill=color,outline="#d5c28f" if id==selected else "",tags=("mesh","obj:"+id))
        status.set(f"{len(scene.instances)} objects | {len(rows)} CPU preview triangles | right-drag orbit, wheel zoom"+(" | GL unavailable: "+failure if failure else ""))
    def sync():
        objects.delete(0,"end")
        for i,item in enumerate(scene.instances):
            objects.insert("end",item.id)
            if item.id==selected:objects.selection_set(i)
        item=next((i for i in scene.instances if i.id==selected),None)
        if item:
            for k,v in values.items():v.set(str(getattr(item,k)))
        draw()
    def select(event=None):
        nonlocal selected
        ids=objects.curselection()
        if ids:selected=scene.instances[ids[0]].id;sync()
    def pick(e):
        nonlocal selected
        if use_gl.get() and renderer is not None:
            rw,rh=render_size
            selected=renderer.pick(int(e.x*rw/max(1,canvas.winfo_width())),int(e.y*rh/max(1,canvas.winfo_height())))
            sync();return
        for item in reversed(canvas.find_overlapping(e.x-1,e.y-1,e.x+1,e.y+1)):
            tags=canvas.gettags(item)
            tag=next((t for t in tags if t.startswith("obj:")),None)
            if tag:selected=tag[4:];sync();return
    def apply():
        if not selected:return
        try:scene.update(selected,**{k:float(v.get()) for k,v in values.items()});sync()
        except ValueError as e:messagebox.showerror("Transform",str(e))
    def add():
        nonlocal selected
        n=1
        while any(i.id==f"tree-new-{n}" for i in scene.instances):n+=1
        if "tree" not in scene.assets:return
        selected=f"tree-new-{n}";scene.add(Instance(selected,"tree"));sync()
    def delete():
        nonlocal selected
        if selected and any(i.id==selected for i in scene.instances):
            scene.remove(selected);selected=None;sync()
    def open_scene():
        nonlocal scene,selected
        p=filedialog.askopenfilename(filetypes=[("Chimster scene","*.json")])
        if p:
            try:scene=Scene.load(p);selected=None;sync()
            except (OSError,ValueError,KeyError,TypeError) as e:messagebox.showerror("Scene",str(e))
    def save_scene():
        p=filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            try:scene.save(p)
            except (OSError,ValueError) as e:messagebox.showerror("Scene",str(e))
    def import_mesh():
        nonlocal selected
        p=filedialog.askopenfilename(filetypes=[("Triangulated OBJ","*.obj")])
        if p:
            try:
                m=load_obj(p);n=1
                while f"import-{n}" in scene.assets:n+=1
                key=f"import-{n}";scene.assets[key]=m;scene.add(Instance(key,key));selected=key;sync()
            except (OSError,ValueError) as e:messagebox.showerror("Mesh",str(e))
    def start(e):
        nonlocal drag
        drag=(e.x,e.y)
    def orbit(e):
        nonlocal drag,camera
        if drag:
            dx,dy=e.x-drag[0],e.y-drag[1];drag=(e.x,e.y)
            camera=replace(camera,yaw=camera.yaw+dx*.5,pitch=max(-85,min(85,camera.pitch+dy*.5)));draw()
    def zoom(delta):
        nonlocal camera
        camera=replace(camera,zoom=max(.05,min(2000,camera.zoom*(1.15 if delta>0 else 1/1.15))));draw()
    def fit():
        nonlocal camera
        from .scene import transformed
        pts=[p for i in scene.instances for p in transformed(scene.assets[i.asset],i)]
        if not pts:return
        lo=[min(p[k] for p in pts) for k in range(3)];hi=[max(p[k] for p in pts) for k in range(3)]
        size=max(1,max(hi[k]-lo[k] for k in range(3)))
        camera=replace(camera,center=tuple((a+b)/2 for a,b in zip(lo,hi)),zoom=max(.05,min(2000,min(canvas.winfo_width(),canvas.winfo_height())*.65/size)));draw()
    def set_lod():
        nonlocal settings
        try:
            thresholds=tuple(float(x.strip()) for x in lod_text.get().split(","))
            settings=replace(settings,lod_distances=thresholds).validate();draw()
        except ValueError as e:messagebox.showerror("LOD settings",str(e))
    def import_materials():
        nonlocal materials
        p=filedialog.askopenfilename(filetypes=[("Material manifest","*.json")])
        if p:
            try:materials=load_materials(p);draw()
            except (OSError,ValueError,TypeError,ImportError) as e:messagebox.showerror("Materials",str(e))
    def release(e):
        nonlocal renderer
        if e.widget is parent and renderer is not None:
            try:renderer.close()
            finally:renderer=None
    parent.bind("<Destroy>",release,add="+")
    controls=ttk.Frame(parent);controls.pack(fill="x",before=pane)
    ttk.Checkbutton(controls,text="OpenGL preview",variable=use_gl,command=draw).pack(side="left")
    ttk.Label(controls,text="LOD distances").pack(side="left")
    ttk.Entry(controls,textvariable=lod_text,width=15).pack(side="left")
    ttk.Button(controls,text="Apply LOD",command=set_lod).pack(side="left")
    ttk.Button(controls,text="Load materials",command=import_materials).pack(side="left")
    for label,cmd in [("Open scene",open_scene),("Save scene",save_scene),("Import OBJ",import_mesh),("Fit",fit),("Add tree",add),("Delete",delete),("Undo",lambda:(scene.undo(),sync())),("Redo",lambda:(scene.redo(),sync()))]:
        ttk.Button(toolbar,text=label,command=cmd).pack(side="left")
    ttk.Button(side,text="Apply transform",command=apply).pack(fill="x")
    objects.bind("<<ListboxSelect>>",select);canvas.bind("<Button-1>",pick);canvas.bind("<Button-3>",start);canvas.bind("<B3-Motion>",orbit)
    canvas.bind("<MouseWheel>",lambda e:zoom(e.delta));canvas.bind("<Button-4>",lambda e:zoom(1));canvas.bind("<Button-5>",lambda e:zoom(-1))
    canvas.bind("<Configure>",lambda e:draw());sync()
