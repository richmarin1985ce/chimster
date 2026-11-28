"""Font Forge: local font import, preview and basic polygon glyph authoring."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from .font_library import FontLibrary, drop_paths
from .font_forge import create

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
    listing.bind("<<TreeviewSelect>>",render)
    sample.trace_add("write",render)
    size.trace_add("write",render)
    refresh()
    render()

    family = tk.StringVar(value="My Font")
    character = tk.StringVar(value="A")
    fields = ttk.Frame(author)
    fields.pack(fill="x")
    ttk.Label(fields,text="Family").pack(side="left")
    ttk.Entry(fields,textvariable=family,width=22).pack(side="left")
    ttk.Label(fields,text="Character").pack(side="left")
    ttk.Entry(fields,textvariable=character,width=8).pack(side="left")
    ttk.Label(author,text="Click outline vertices, close each contour, then save the glyph. Reverse winding for holes.").pack(anchor="w")
    canvas = tk.Canvas(author,width=400,height=300,bg="white",highlightthickness=1)
    canvas.pack(anchor="w")
    contours, active, glyphs = [], [], {}
    note = tk.StringVar(value="0 glyphs saved")
    def redraw():
        canvas.delete("all")
        for x in range(20,381,40):
            canvas.create_line(x,10,x,290,fill="#eeeeee")
        for y in range(10,291,40):
            canvas.create_line(20,y,380,y,fill="#eeeeee")
        canvas.create_line(20,250,380,250,fill="#888888",dash=(3,3))
        for points in contours:
            canvas.create_polygon(*[v for p in points for v in p],fill="",outline="black",width=2)
        if len(active)>1:
            canvas.create_line(*[v for p in active for v in p],fill="#3366aa",width=2)
        for x,y in active:
            canvas.create_oval(x-2,y-2,x+2,y+2,fill="#3366aa",outline="")
    def click(event):
        if 20<=event.x<=380 and 10<=event.y<=290:
            active.append((event.x,event.y))
            redraw()
    def close():
        if len(active)>=3:
            contours.append(active.copy())
            active.clear()
            redraw()
    def undo():
        if active:
            active.pop()
        elif contours:
            active.extend(contours.pop())
        redraw()
    def clear():
        active.clear()
        contours.clear()
        redraw()
    def save_glyph():
        value = character.get()
        if len(value)!=1 or ord(value)<33 or 0xd800<=ord(value)<=0xdfff or active or not contours:
            messagebox.showerror("Glyph","Use one non-space Unicode character and close all contours.",parent=parent)
            return
        glyphs[ord(value)] = [[(round((x-20)*2.5),round((250-y)*2.5)) for x,y in contour] for contour in contours]
        note.set(f"{len(glyphs)} glyphs saved; last: U+{ord(value):04X}")
        clear()
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
    actions = ttk.Frame(author)
    actions.pack(fill="x")
    for label,command in (("Close contour",close),("Undo",undo),("Clear drawing",clear),("Save glyph",save_glyph),("Export TTF",export)):
        ttk.Button(actions,text=label,command=command).pack(side="left")
    ttk.Label(author,textvariable=note).pack(anchor="w")
    redraw()
