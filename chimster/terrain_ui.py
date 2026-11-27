"""Interactive top-down terrain brush editor with synchronized 3D preview."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
import json
from .worldspace import Terrain,TerrainHistory
from .land_paint import Paint
from .lod import terrain_grid
from .scene import Scene,Instance,Camera,frame

def mount(parent):
    h=TerrainHistory(Terrain(tuple(tuple(0. for x in range(65)) for y in range(65)),4,0))
    paint=Paint(tuple(tuple("Ground" for x in range(4)) for y in range(4)))
    layers=[];past=[];future=[];photo=None
    mode=tk.StringVar(value="Raise");radius=tk.DoubleVar(value=4);amount=tk.DoubleVar(value=1)
    target=tk.DoubleVar(value=0)
    spacing=tk.DoubleVar(value=4);material=tk.StringVar(value="Ground")
    bar=ttk.Frame(parent);bar.pack(fill="x")
    ttk.Combobox(bar,textvariable=mode,values=("Raise","Lower","Smooth","Flatten","Paint","Blend","Erase"),state="readonly",width=8).pack(side="left")
    for name,var in [("Radius",radius),("Height m",amount),("Target m",target),("Spacing m",spacing),("Texture ID",material)]:
        ttk.Label(bar,text=name).pack(side="left");ttk.Entry(bar,textvariable=var,width=9).pack(side="left")
    panes=ttk.Panedwindow(parent,orient="horizontal");panes.pack(fill="both",expand=True)
    mapview=tk.Canvas(panes,bg="#222a32",width=380,height=380);view=tk.Canvas(panes,bg="#19232c",width=400,height=380)
    panes.add(mapview,weight=1);panes.add(view,weight=1)
    status=tk.StringVar();ttk.Label(parent,textvariable=status).pack(fill="x")
    def draw():
        nonlocal photo
        from PIL import Image,ImageTk
        t=h.current;n=len(t.heights);w=max(1,mapview.winfo_width());hh=max(1,mapview.winfo_height());size=min(w,hh)
        lo=min(map(min,t.heights));hi=max(map(max,t.heights));span=max(.01,hi-lo)
        im=Image.new("RGB",(n,n));pixels=[]
        import hashlib
        from .blended_paint import index
        groups=index(layers,t.cells)
        color_cache={}
        def shade(tex):
            if tex not in color_cache:color_cache[tex]=tuple(65+v*.6 for v in hashlib.sha256(tex.encode()).digest()[:3])
            return color_cache[tex]
        for j in range(n-1,-1,-1):
            for i,z in enumerate(t.heights[j]):
                q=paint.rows[min(len(paint.rows)-1,j//16)][min(len(paint.rows)-1,i//16)]
                qx=min(len(paint.rows)-1,i//16);qy=min(len(paint.rows)-1,j//16)
                pos=(j-qy*16)*17+i-qx*16;c=shade(q)
                for tex,vertices in groups.get((qx//2,qy//2,(qy%2)*2+qx%2),[]):
                    a=vertices.get(pos,0.);v=shade(tex);c=tuple(old*(1-a)+new*a for old,new in zip(c,v))
                light=.35+.65*(z-lo)/span
                pixels.append(tuple(int(v*light) for v in c))
        im.putdata(pixels);photo=ImageTk.PhotoImage(im.resize((size,size),Image.Resampling.NEAREST))
        mapview.delete("all");mapview.create_image(0,0,image=photo,anchor="nw")
        # Preview a regular decimated grid, never alter source heights.
        step=max(1,(n-1)//32)
        mesh=terrain_grid([list(row[::step]) for row in t.heights[::step]],spacing=t.spacing_m*step)
        scene=Scene({"terrain":mesh},[Instance("ground","terrain")])
        vw,vh=max(1,view.winfo_width()),max(1,view.winfo_height())
        extent=(n-1)*t.spacing_m;cam=Camera(zoom=min(vw,vh)*.65/max(extent,span,1),center=(extent/2,extent/2,(lo+hi)/2))
        view.delete("all")
        for _,_,coords,color in frame(scene,cam,vw,vh):view.create_polygon(*coords,fill=color,outline="#334434")
        status.set(f"{n} × {n} | {t.cells*t.cells} cells | {lo:.2f}–{hi:.2f} m | Overlay allocations: {len(layers)} | 4 overlays max/quad")
    def edit(e):
        nonlocal paint,layers
        try:
            size=min(mapview.winfo_width(),mapview.winfo_height())
            if not 0<=e.x<size or not 0<=e.y<size:return
            n=len(h.current.heights);x=e.x/size*(n-1);y=(1-e.y/size)*(n-1)
            before=(h.current,paint,layers)
            if mode.get()=="Paint":
                updated=paint.brush(x/16-.5,y/16-.5,max(.5,radius.get()/16),material.get())
                for entry in layers:
                    cx,cy=entry["cell"];q=entry["quadrant"]
                    if updated.rows[cy*2+q//2][cx*2+q%2]==entry["texture"]:raise ValueError("base replacement matches an allocated overlay")
                paint=updated
            elif mode.get() in ("Blend","Erase"):
                from .blended_paint import stroke
                layers=stroke(paint,layers,x,y,radius.get(),min(1,max(0,amount.get())),material.get(),mode.get()=="Erase")
            elif mode.get() in ("Smooth","Flatten"):
                from .world_tools import brush
                h.current=brush(h.current,x,y,radius.get(),mode.get().lower(),min(1,max(0,amount.get())),target.get())
            else:
                h.current=h.current.sculpt(x,y,radius.get(),amount.get()*(1 if mode.get()=="Raise" else -1))
            past.append(before);past[:]=past[-10:];future.clear();draw()
        except (ValueError,tk.TclError) as e:messagebox.showerror("Terrain brush",str(e))
    def history(src,dst):
        nonlocal paint,layers
        if src:
            dst.append((h.current,paint,layers));h.current,paint,layers=src.pop();draw()
    def load():
        nonlocal paint,layers
        p=filedialog.askopenfilename(filetypes=[("Elevation JSON","*.json")])
        if not p:return
        try:
            t=Terrain.load(p,spacing.get());h.current=t;paint=Paint(tuple(tuple("Ground" for _ in range(t.cells*2)) for _ in range(t.cells*2)))
            layers=[];past.clear();future.clear();draw()
        except (OSError,ValueError,TypeError,tk.TclError) as e:messagebox.showerror("Terrain",str(e))
    def reopen():
        nonlocal paint,layers
        d=filedialog.askdirectory(title="Open saved terrain project")
        if not d:return
        try:
            p=Path(d);m=json.loads((p/"metadata.json").read_text(encoding="utf-8"))
            t=Terrain.load(p/"elevation-meters.json",m["spacing_m"],m["datum_m"])
            q=Paint(tuple(tuple(r) for r in json.loads((p/"paint.json").read_text(encoding="utf-8")))).validate(t.cells)
            from .blended_paint import index
            alpha=json.loads((p/"alpha_layers.json").read_text(encoding="utf-8")) if (p/"alpha_layers.json").exists() else []
            index(alpha,t.cells)
            h.current=t;paint=q;layers=alpha;spacing.set(t.spacing_m);past.clear();future.clear();draw()
        except (OSError,ValueError,KeyError,TypeError) as e:messagebox.showerror("Terrain",str(e))
    def save():
        d=filedialog.askdirectory(title="Select parent for new terrain project")
        if not d:return
        try:
            p=Path(d)/"terrain-edit";p.mkdir(exist_ok=False)
            (p/"elevation-meters.json").write_text(json.dumps(h.current.heights),encoding="utf-8")
            (p/"paint.json").write_text(json.dumps(paint.rows),encoding="utf-8")
            (p/"alpha_layers.json").write_text(json.dumps(layers),encoding="utf-8")
            (p/"metadata.json").write_text(json.dumps({"spacing_m":h.current.spacing_m,"datum_m":h.current.datum_m}),encoding="utf-8")
            messagebox.showinfo("Saved",str(p))
        except OSError as e:messagebox.showerror("Terrain",str(e))
    buttons=ttk.Frame(parent);buttons.pack(fill="x")
    for label,fn in [("Import heights",load),("Reopen project",reopen),("Undo",lambda:history(past,future)),("Redo",lambda:history(future,past)),("Save terrain project",save)]:
        ttk.Button(buttons,text=label,command=fn).pack(side="left")
    mapview.bind("<Button-1>",edit)
    # Draw lazily; Pillow is optional in source installs.
    def resize(e=None):
        try:draw()
        except ImportError:status.set("Install Pillow to use the terrain editor.")
    mapview.bind("<Configure>",resize);view.bind("<Configure>",resize)
