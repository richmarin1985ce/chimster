"""Shared imported-font selection for editor surfaces."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from .font_library import FontLibrary

class FontPicker:
    def __init__(self,parent,allow_default=True):
        self.frame=ttk.Frame(parent)
        self.variable=tk.StringVar(master=parent)
        self.allow_default=allow_default
        self.rows={}
        self.combo=ttk.Combobox(self.frame,textvariable=self.variable,state="readonly",width=33)
        self.combo.pack(side="left")
        ttk.Button(self.frame,text="Refresh fonts",command=self.refresh).pack(side="left")
        self.refresh()
    def refresh(self):
        previous=self.path()
        self.rows={}
        try:
            for path,info in FontLibrary().entries():
                label=f'{info["family"]} / {info["style"]} [{path.stem[:12]}]'
                self.rows[label]=path
        except (OSError,ImportError):pass
        options=(["Default preview"] if self.allow_default else [])+list(self.rows)
        self.combo.configure(values=options)
        self.variable.set(next((key for key,p in self.rows.items() if p==previous),options[0] if options else ""))
    def path(self):
        return self.rows.get(self.variable.get())

def text_asset_dialog(parent):
    from .font_render import render_text,export_text_png
    from PIL import ImageTk
    win=tk.Toplevel(parent);win.title("Font Forge — text asset")
    picker=FontPicker(win,False);picker.frame.pack(fill="x")
    text=tk.Text(win,height=4,width=60);text.pack(fill="x")
    text.insert("1.0","Your text")
    size=tk.StringVar(value="48")
    ttk.Spinbox(win,from_=8,to=144,textvariable=size,width=6).pack(anchor="w")
    preview=ttk.Label(win);preview.pack(fill="both",expand=True)
    permission=tk.BooleanVar(value=False)
    ttk.Checkbutton(win,text="I have rights to distribute this rendered text",variable=permission).pack(anchor="w")
    def inputs():
        if picker.path() is None:raise ValueError("Import a font in Font Forge first")
        return picker.path(),text.get("1.0","end-1c"),int(size.get())
    def show():
        try:
            source,value,points=inputs()
            preview.image=ImageTk.PhotoImage(render_text(source,value,points,720,256),master=win)
            preview.configure(image=preview.image)
        except (ValueError,OSError,ImportError) as exc:messagebox.showerror("Font asset",str(exc),parent=win)
    def export():
        try:
            source,value,points=inputs()
            path=filedialog.asksaveasfilename(parent=win,defaultextension=".png",filetypes=[("PNG","*.png")])
            if path:export_text_png(source,path,value,points,720,256,permission.get())
        except (ValueError,OSError,ImportError) as exc:messagebox.showerror("Font asset",str(exc),parent=win)
    ttk.Button(win,text="Preview",command=show).pack(side="left")
    ttk.Button(win,text="Export transparent PNG",command=export).pack(side="left")
