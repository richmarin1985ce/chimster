"""Local book authoring tab. No game writes."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .books import Book,GAMES,load,export
def mount(parent):
    fields={k:tk.StringVar(value=v) for k,v in {"editor_id":"ChimsterBook","title":"Untitled","author":"","kind":"book","game":"newvegas"}.items()}
    for k,var in fields.items():
        row=ttk.Frame(parent);row.pack(fill="x",pady=2)
        ttk.Label(row,text=k,width=12).pack(side="left")
        if k in ("kind","game"):ttk.Combobox(row,textvariable=var,values=("book","note","journal") if k=="kind" else sorted(GAMES),state="readonly").pack(side="left",fill="x",expand=True)
        else:ttk.Entry(row,textvariable=var).pack(side="left",fill="x",expand=True)
    ttk.Label(parent,text="Separate pages with a line containing ---PAGE---. Plain text; preview is not the game font/layout.").pack(anchor="w")
    text=tk.Text(parent,wrap="word");text.pack(fill="both",expand=True)
    from .book_fonts import choices,font_tag,references
    fontbar=ttk.Frame(parent);fontbar.pack(fill="x",before=text)
    ttk.Label(fontbar,text="Native font").pack(side="left")
    face=ttk.Combobox(fontbar,state="readonly",width=25);face.pack(side="left")
    def update_fonts(*args):
        options=choices(fields["game"].get());face.configure(values=options)
        face.set(options[0] if options else "")
    fields["game"].trace_add("write",update_fonts);update_fonts()
    def insert_font():
        try:
            start=text.index("sel.first");end=text.index("sel.last")
            selected=text.get(start,end)
            tag=font_tag(fields["game"].get(),face.get())
            text.delete(start,end);text.insert(start,tag+selected+"</FONT>")
        except tk.TclError:messagebox.showinfo("Font","Select a passage first.")
        except ValueError as e:messagebox.showerror("Font",str(e))
    ttk.Button(fontbar,text="Apply to selection",command=insert_font).pack(side="left")
    def book():
        import re
        return Book(**{k:v.get() for k,v in fields.items()},pages=tuple(re.split(r"\n---PAGE---\n",text.get("1.0","end-1c")))).validate()
    def open_book():
        p=filedialog.askopenfilename(filetypes=[("Book project","*.json")])
        if not p:return
        try:
            b=load(p)
            for k,v in fields.items():v.set(getattr(b,k))
            text.delete("1.0","end");text.insert("1.0","\n---PAGE---\n".join(b.pages))
        except (OSError,ValueError,TypeError) as e:messagebox.showerror("Book",str(e))
    def write():
        parentdir=filedialog.askdirectory(title="Choose parent for new book output")
        if not parentdir:return
        try:
            b=book();p=Path(parentdir)/b.editor_id;export(b,p)
            messagebox.showinfo("Book exported",str(p))
        except (OSError,ValueError,TypeError) as e:messagebox.showerror("Book",str(e))
    def page_preview():
        try:
            b=book()
            win=tk.Toplevel(parent);win.title(b.title)
            index=0
            heading=ttk.Label(win);heading.pack()
            page=tk.Text(win,wrap="word",width=65,height=22,padx=20,pady=20)
            page.pack(fill="both",expand=True);page._book_fonts=[]
            def show(delta=0):
                nonlocal index
                index=max(0,min(len(b.pages)-1,index+delta))
                heading.configure(text=f"{b.title} — {index+1}/{len(b.pages)}")
                page.configure(state="normal");page.delete("1.0","end")
                for tag in page.tag_names():
                    if tag!="sel":page.tag_delete(tag)
                page._book_fonts.clear()
                from .book_markup import runs
                import tkinter.font as tkfont
                fonts={}
                for value,styles in runs(b.pages[index]):
                    key=tuple(styles)
                    if key not in fonts:
                        name="style"+str(len(fonts));fonts[key]=name
                        kinds={t for t,a in styles}
                        font=tkfont.Font(root=win,font=page.cget("font"))
                        font.configure(weight="bold" if "b" in kinds else "normal",slant="italic" if "i" in kinds else "roman",underline="u" in kinds)
                        align=next((a for t,a in reversed(styles) if a in ("left","center","right")), "center" if "center" in kinds else "left")
                        page.tag_configure(name,font=font,justify=align)
                        page._book_fonts.append(font)
                    page.insert("end",value,fonts[key])
                page.configure(state="disabled")
            bar=ttk.Frame(win);bar.pack()
            ttk.Button(bar,text="Previous",command=lambda:show(-1)).pack(side="left")
            ttk.Button(bar,text="Next",command=lambda:show(1)).pack(side="left")
            show()
        except (ValueError,TypeError) as e:messagebox.showerror("Book",str(e))
    def validate():
        try:b=book();messagebox.showinfo("Book",f"{len(b.pages)} pages; {sum(map(len,b.pages))} characters. Valid portable project. Native font references: {references(chr(10).join(b.pages))}")
        except (ValueError,TypeError) as e:messagebox.showerror("Book",str(e))
    def native():
        from .fnv_content import export_book
        from tkinter import simpledialog
        try:
            b=book();model=None
            if b.kind=="book":
                model=simpledialog.askstring("Book model","Relative NIF path under meshes (required)")
                if not model:return
            p=filedialog.asksaveasfilename(defaultextension=".esp",filetypes=[("New Vegas plugin","*.esp")])
            if not p:return
            export_book(b,p,model);messagebox.showinfo("Experimental ESP",p+"\nValidate in xEdit and game before use.")
        except (ValueError,TypeError,OSError) as e:messagebox.showerror("Book",str(e))
    bar=ttk.Frame(parent);bar.pack(fill="x")
    for label,cmd in [("Open",open_book),("Validate",validate),("Page preview",page_preview),("Export project + preview",write),("Export FNV ESP",native)]:ttk.Button(bar,text=label,command=cmd).pack(side="left")
