"""Desktop procedural rock generator with wireframe preview."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .rock_gen import RockRecipe,generate
from .flora import write_obj

def mount(parent):
    fields={}
    controls=ttk.Frame(parent);controls.pack(fill="x")
    for i,(name,value) in enumerate(vars(RockRecipe()).items()):
        ttk.Label(controls,text=name.capitalize()).grid(row=i//3*2,column=i%3,sticky="w")
        v=tk.StringVar(value=str(value));fields[name]=v
        ttk.Entry(controls,textvariable=v,width=16).grid(row=i//3*2+1,column=i%3,sticky="ew")
    canvas=tk.Canvas(parent,background="#202631",height=360)
    canvas.pack(fill="both",expand=True)
    status=tk.StringVar(value="Intermediate OBJ; native export not verified.")
    ttk.Label(parent,textvariable=status).pack(fill="x")
    def mesh():
        return generate(RockRecipe(seed=int(fields["seed"].get()),detail=int(fields["detail"].get()),
            **{k:float(fields[k].get()) for k in ("width","depth","height","roughness")}))
    def preview():
        m=mesh();canvas.delete("all")
        points=[(x-.55*y,z+.3*y) for x,y,z in m.vertices]
        lo=[min(p[i] for p in points) for i in (0,1)]
        hi=[max(p[i] for p in points) for i in (0,1)]
        w=max(canvas.winfo_width(),100);h=max(canvas.winfo_height(),100)
        scale=min((w-30)/max(hi[0]-lo[0],.001),(h-30)/max(hi[1]-lo[1],.001))
        pts=[(w/2+(x-(lo[0]+hi[0])/2)*scale,h/2-(y-(lo[1]+hi[1])/2)*scale) for x,y in points]
        for face,_ in m.faces:
            canvas.create_polygon(*(v for i in face for v in pts[i]),fill="",outline="#9ab5c9")
        status.set(f"{len(m.vertices)} vertices | {len(m.faces)} triangles | OBJ prototype")
    def export():
        m=mesh()
        p=filedialog.asksaveasfilename(defaultextension=".obj",filetypes=[("Wavefront OBJ","*.obj")])
        if p:write_obj(m,p);status.set("Exported "+p)
    def guard(fn):
        def run():
            try:fn()
            except (ValueError,OSError,OverflowError) as e:messagebox.showerror("Asset Forge",str(e))
        return run
    bar=ttk.Frame(parent);bar.pack(fill="x")
    ttk.Button(bar,text="Generate preview",command=guard(preview)).pack(side="left")
    ttk.Button(bar,text="Export OBJ",command=guard(export)).pack(side="left")
