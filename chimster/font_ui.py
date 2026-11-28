"""Font Forge: local font import, preview and basic polygon glyph authoring."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from .font_library import FontLibrary, drop_paths
from .font_forge import create
from .font_project import nodes, segments, save_project, load_project
from .font_strokes import Sample,outline

def mount(parent):
    library = FontLibrary()
    tabs = ttk.Notebook(parent)
    tabs.pack(fill="both", expand=True)
    browse = ttk.Frame(tabs, padding=8)
    author = ttk.Frame(tabs, padding=8)
    tabs.add(browse, text="Font library")
    tabs.add(author, text="Create TTF")
    status = tk.StringVar(value="Drop .ttf or .otf files here, or browse.")
    drop = ttk.Label(browse, textvariable=status, anchor="center", padding=14, relief="groove")
    drop.pack(fill="x")
    bar = ttk.Frame(browse)
    bar.pack(fill="x")
    listing = ttk.Treeview(browse, columns=("family","style","count","format"), show="headings", height=5, selectmode="browse")
    for col, label, width in (("family","Family",190),("style","Style",120),("count","Characters",90),("format","Format",75)):
        listing.heading(col,text=label)
        listing.column(col,width=width)
    listing.pack(fill="x")
    sample = tk.StringVar(value="The quick brown fox jumps over the lazy dog. 0123456789")
    ttk.Entry(browse,textvariable=sample).pack(fill="x",pady=4)
    size = tk.StringVar(value="32")
    ttk.Spinbox(browse,from_=12,to=96,textvariable=size,width=5).pack(anchor="w")
    preview = ttk.Label(browse,anchor="center")
    preview.pack(fill="both",expand=True)
    metadata = tk.StringVar()
    ttk.Label(browse,textvariable=metadata,wraplength=700).pack(fill="x")
    rows = {}
    def refresh():
        previous = listing.selection()
        listing.delete(*listing.get_children())
        rows.clear()
        for path, info in library.entries():
            key = path.name
            rows[key] = (path,info)
            listing.insert("", "end", iid=key, values=(info["family"],info["style"],info["characters"],info["format"]))
        if previous and previous[0] in rows:
            listing.selection_set(previous[0])
    def render(*_):
        selected = listing.selection()
        if not selected or selected[0] not in rows:
            preview.configure(image="",text="Select a font to preview.")
            preview.image = None
            metadata.set("")
            return
        path, info = rows[selected[0]]
        metadata.set("License: "+info["license"][:400]+" | Embedding flags: "+str(info["embedding_flags"])+" | Local preview only")
        try:
            from PIL import Image, ImageDraw, ImageFont, ImageTk
            font = ImageFont.truetype(str(path), max(12,min(96,int(size.get()))))
            image = Image.new("RGB",(720,160),"white")
            draw = ImageDraw.Draw(image)
            draw.text((12,12),sample.get()[:300],font=font,fill="black")
            preview.image = ImageTk.PhotoImage(image,master=parent)
            preview.configure(image=preview.image,text="")
        except (OSError,ValueError,ImportError) as exc:
            preview.configure(image="",text=str(exc))
            preview.image = None
    def add(paths):
        errors = []
        imported = []
        for path in paths:
            try:
                target,_ = library.import_font(path)
                imported.append(target.name)
            except (OSError,ValueError,ImportError) as exc:
                errors.append(Path(path).name+": "+str(exc))
        refresh()
        if imported:
            listing.selection_set(imported[-1])
            listing.see(imported[-1])
        render()
        status.set(f"{len(imported)} font(s) accepted; {len(errors)} rejected.")
        if errors:
            messagebox.showwarning("Font import","\n".join(errors),parent=parent)
    def dropped(event):
        try:
            add(drop_paths(drop,event.data))
        except tk.TclError as exc:
            messagebox.showerror("Font drop",str(exc),parent=parent)
        return "copy"
    try:
        from tkinterdnd2 import DND_FILES
        drop.drop_target_register(DND_FILES)
        drop.dnd_bind("<<Drop>>",dropped)
        listing.drop_target_register(DND_FILES)
        listing.dnd_bind("<<Drop>>",dropped)
    except (ImportError,AttributeError,tk.TclError):
        status.set("Native file drop unavailable; use Browse fonts.")
    ttk.Button(bar,text="Browse fonts",command=lambda:add(filedialog.askopenfilenames(parent=parent,filetypes=[("Fonts","*.ttf *.otf")]))).pack(side="left")
    ttk.Button(bar,text="Refresh",command=refresh).pack(side="left")
    from .font_picker import text_asset_dialog
    ttk.Button(bar,text="Text asset",command=lambda:text_asset_dialog(parent)).pack(side="left")
    listing.bind("<<TreeviewSelect>>",render)
    sample.trace_add("write",render)
    size.trace_add("write",render)
    refresh()
    render()

    family = tk.StringVar(value="My Font")
    character = tk.StringVar(value="A")
    mode = tk.StringVar(value="On-curve")
    fields = ttk.Frame(author)
    fields.pack(fill="x")
    ttk.Label(fields,text="Family").pack(side="left")
    ttk.Entry(fields,textvariable=family,width=22).pack(side="left")
    ttk.Label(fields,text="Character").pack(side="left")
    ttk.Entry(fields,textvariable=character,width=8).pack(side="left")
    ttk.Combobox(fields,textvariable=mode,values=("On-curve","Control point","Move point","Freehand"),state="readonly",width=15).pack(side="left")
    ttk.Label(author,text="Click to add points; control points form curves. Move point mode drags nodes. Reverse winding for holes.").pack(anchor="w")
    stroke_width=tk.StringVar(value="40")
    smoothing=tk.StringVar(value="1")
    ttk.Label(fields,text="Stroke").pack(side="left")
    ttk.Spinbox(fields,from_=5,to=200,textvariable=stroke_width,width=5).pack(side="left")
    ttk.Label(fields,text="Smooth").pack(side="left")
    ttk.Spinbox(fields,from_=0,to=3,textvariable=smoothing,width=3).pack(side="left")
    canvas = tk.Canvas(author,width=400,height=300,bg="white",highlightthickness=1)
    canvas.pack(anchor="w")
    contours, active, glyphs = [], [], {}
    dragging = []
    stroke=[]
    note = tk.StringVar(value="0 glyphs saved")
    def screen(p):
        return (20+p[0]/2.5,250-p[1]/2.5)
    def em(x,y,on):
        return (round((x-20)*2.5),round((250-y)*2.5),on)
    def redraw():
        canvas.delete("all")
        for x in range(20,381,40):
            canvas.create_line(x,10,x,290,fill="#eeeeee")
        for y in range(10,291,40):
            canvas.create_line(20,y,380,y,fill="#eeeeee")
        canvas.create_line(20,250,380,250,fill="#888888",dash=(3,3))
        for points in contours:
            for a,c,b in segments(points):
                if c is None:
                    path=[screen(a),screen(b)]
                else:
                    path=[screen(tuple((1-t)**2*a[i]+2*t*(1-t)*c[i]+t*t*b[i] for i in (0,1))) for t in (n/24 for n in range(25))]
                canvas.create_line(*[v for p in path for v in p],fill="black",width=2)
        if len(stroke)>1:
            canvas.create_line(*[v for p in stroke for v in screen((p.x,p.y))],fill="#3366aa",width=2)
        if len(active)>1:
            canvas.create_line(*[v for p in active for v in screen(p)],fill="#3366aa",dash=(3,3),width=2)
        for points in contours+[active]:
            for p in points:
                x,y=screen(p)
                if p[2]:
                    canvas.create_oval(x-3,y-3,x+3,y+3,fill="#3366aa",outline="")
                else:
                    canvas.create_rectangle(x-3,y-3,x+3,y+3,fill="#b56b21",outline="")
    def click(event):
        dragging.clear()
        if mode.get()=="Freehand":
            if active:
                messagebox.showinfo("Stroke","Close or clear the active contour first.",parent=parent)
                return
            stroke.clear()
            if 20<=event.x<=380 and 10<=event.y<=290:
                x,y,_=em(event.x,event.y,True);stroke.append(Sample(x,y))
            return
        if mode.get()=="Move point":
            candidates=[]
            for points in contours+[active]:
                for i,p in enumerate(points):
                    x,y=screen(p)
                    candidates.append(((x-event.x)**2+(y-event.y)**2,points,i))
            if candidates:
                d,points,i=min(candidates,key=lambda a:a[0])
                if d<=100:dragging.extend((points,i))
            return
        if 20<=event.x<=380 and 10<=event.y<=290:
            if len(active)>=2048:return
            active.append(em(event.x,event.y,not active or mode.get()!="Control point"))
            redraw()
    def move(event):
        if stroke:
            x,y,_=em(max(20,min(380,event.x)),max(10,min(290,event.y)),True)
            if len(stroke)<1000 and (x,y)!=(stroke[-1].x,stroke[-1].y):
                stroke.append(Sample(x,y));redraw()
            return
        if dragging:
            points,i=dragging
            points[i]=em(max(20,min(380,event.x)),max(10,min(290,event.y)),points[i][2])
            redraw()
    def release(event):
        dragging.clear()
        if stroke:
            try:
                if len(contours)>=128:raise ValueError("Too many contours")
                contours.append(outline(stroke,int(stroke_width.get()),int(smoothing.get())))
            except ValueError as exc:messagebox.showerror("Freehand",str(exc),parent=parent)
            finally:stroke.clear();redraw()
    def close():
        try:
            if len(contours)>=128:raise ValueError("Too many contours")
            contours.append(nodes(active))
            active.clear()
            redraw()
        except ValueError as exc:messagebox.showerror("Contour",str(exc),parent=parent)
    def undo():
        if active:
            active.pop()
        elif contours:
            active.extend(contours.pop())
        redraw()
    def clear():
        dragging.clear()
        stroke.clear()
        active.clear()
        contours.clear()
        redraw()
    def codepoint():
        value=character.get()
        if len(value)!=1 or ord(value)<33 or 0xd800<=ord(value)<=0xdfff:
            raise ValueError("Use one non-space Unicode character")
        return ord(value)
    def update_note():
        note.set(f"{len(glyphs)} glyphs saved: "+", ".join(f"U+{cp:04X}" for cp in sorted(glyphs)[:18]))
    def save_glyph():
        try:
            cp=codepoint()
            if active or not contours:raise ValueError("Close all contours before saving")
            if cp not in glyphs and len(glyphs)>=4096:raise ValueError("Too many glyphs")
            if cp in glyphs and not messagebox.askyesno("Glyph","Replace saved glyph?",parent=parent):return
            glyphs[cp]=[nodes(c) for c in contours]
            update_note()
            clear()
        except ValueError as exc:messagebox.showerror("Glyph",str(exc),parent=parent)
    def edit_glyph():
        try:
            cp=codepoint()
            if cp not in glyphs:raise ValueError("No saved glyph for this character")
            if (active or contours) and not messagebox.askyesno("Glyph","Discard the unsaved drawing?",parent=parent):return
            clear()
            contours.extend([list(c) for c in glyphs[cp]])
            redraw()
        except ValueError as exc:messagebox.showerror("Glyph",str(exc),parent=parent)
    def delete_glyph():
        try:
            cp=codepoint()
            if cp in glyphs and messagebox.askyesno("Glyph","Delete saved glyph?",parent=parent):
                del glyphs[cp]
                update_note()
        except ValueError as exc:messagebox.showerror("Glyph",str(exc),parent=parent)
    def save():
        if active or contours:
            messagebox.showerror("Font project","Save or clear the current drawing first.",parent=parent)
            return
        path=filedialog.asksaveasfilename(parent=parent,defaultextension=".json",filetypes=[("Font project","*.json")])
        if path:
            try:save_project(path,family.get(),glyphs)
            except (OSError,ValueError) as exc:messagebox.showerror("Font project",str(exc),parent=parent)
    def load():
        path=filedialog.askopenfilename(parent=parent,filetypes=[("Font project","*.json")])
        if not path:return
        try:
            name,new=load_project(path)
            if (glyphs or active or contours) and not messagebox.askyesno("Font project","Replace the current font project?",parent=parent):return
            clear()
            glyphs.clear()
            glyphs.update(new)
            family.set(name)
            update_note()
        except (OSError,ValueError) as exc:messagebox.showerror("Font project",str(exc),parent=parent)
    def export():
        if active or contours:
            messagebox.showerror("Font","Save or clear the current glyph before export.",parent=parent)
            return
        path = filedialog.asksaveasfilename(parent=parent,defaultextension=".ttf",filetypes=[("TrueType","*.ttf")])
        if path:
            try:
                create(family.get(),glyphs,path)
                add([path])
                tabs.select(browse)
            except (OSError,ValueError,ImportError) as exc:
                messagebox.showerror("Font",str(exc),parent=parent)
    canvas.bind("<Button-1>",click)
    canvas.bind("<B1-Motion>",move)
    canvas.bind("<ButtonRelease-1>",release)
    actions = ttk.Frame(author)
    actions.pack(fill="x")
    for label,command in (("Close contour",close),("Undo point",undo),("Clear drawing",clear),("Save glyph",save_glyph),("Edit glyph",edit_glyph),("Delete glyph",delete_glyph)):
        ttk.Button(actions,text=label,command=command).pack(side="left")
    projectbar=ttk.Frame(author)
    projectbar.pack(fill="x")
    for label,command in (("Open project",load),("Save project",save),("Export TTF",export)):
        ttk.Button(projectbar,text=label,command=command).pack(side="left")
    ttk.Label(author,textvariable=note).pack(anchor="w")
    redraw()
