"""Local source editor; save to new files, never overwrite game scripts."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import queue
import threading
from .script_syntax import LANGUAGES, language_for, spans, export
from .script_lint import check

COLORS = {"comment":"#82946e", "string":"#e4bd7c", "constant":"#b5a1ef",
          "keyword":"#e48aa6", "storage":"#79c4d3", "entity":"#a0d88e"}

def mount(frame, game):
    language = tk.StringVar(value=language_for(game.get()))
    status = tk.StringVar(value="New script — save a new copy before compiling")
    saved = {"path":None,"text":None}
    pending = [None]
    busy = [False]
    bar = ttk.Frame(frame); bar.pack(fill="x")
    ttk.Label(bar,text="Language").pack(side="left")
    selector = ttk.Combobox(bar,textvariable=language,values=list(LANGUAGES),state="readonly",width=14)
    selector.pack(side="left")
    pane = ttk.Panedwindow(frame,orient="vertical"); pane.pack(fill="both",expand=True)
    area = ttk.Frame(pane); pane.add(area,weight=4)
    gutter = tk.Text(area,width=6,wrap="none",state="disabled",background="#20262c",
                     foreground="#89929e",font="TkFixedFont",takefocus=False)
    gutter.pack(side="left",fill="y")
    editor = tk.Text(area,wrap="none",undo=True,maxundo=100,font="TkFixedFont",
                     background="#181d22",foreground="#d9e0e6",insertbackground="white")
    editor.pack(side="left",fill="both",expand=True)
    scroll = ttk.Scrollbar(area,orient="vertical",command=editor.yview); scroll.pack(side="right",fill="y")
    def yscroll(first,last):
        scroll.set(first,last); gutter.yview_moveto(first)
    editor.configure(yscrollcommand=yscroll)
    results = tk.Text(pane,height=8,wrap="word",font="TkFixedFont",state="disabled")
    pane.add(results,weight=1)
    ttk.Label(frame,textvariable=status).pack(fill="x")
    def report(obj):
        results.configure(state="normal"); results.delete("1.0","end")
        results.insert("1.0",json.dumps(obj,indent=2,ensure_ascii=False))
        results.configure(state="disabled")
    for key,color in COLORS.items():
        editor.tag_configure("syntax_"+key,foreground=color)
    def source():
        return editor.get("1.0","end-1c")
    def refresh():
        pending[0]=None
        if not editor.winfo_exists():return
        content=source()
        for key in COLORS:editor.tag_remove("syntax_"+key,"1.0","end")
        gutter.configure(state="normal");gutter.delete("1.0","end")
        count=content.count("\n")+1
        gutter.insert("1.0","\n".join(str(i) for i in range(1,min(count,50000)+1)))
        gutter.configure(state="disabled");gutter.yview_moveto(editor.yview()[0])
        try:
            for a,b,scope in spans(content,language.get()):
                editor.tag_add("syntax_"+scope.split(".")[0],"1.0+%dc"%a,"1.0+%dc"%b)
        except ValueError as exc:status.set(str(exc))
    def schedule(*_):
        if pending[0] is not None:editor.after_cancel(pending[0])
        pending[0]=editor.after(180,refresh)
    def modified(_=None):
        if editor.edit_modified():
            editor.edit_modified(False);schedule()
            status.set("Modified" if source()!=saved["text"] else "Saved copy")
    editor.bind("<<Modified>>",modified)
    selector.bind("<<ComboboxSelected>>",schedule)
    def open_source():
        if source() and source()!=saved["text"] and not messagebox.askyesno("Discard unsaved edits?","Open another script and discard unsaved edits?"):return
        p=filedialog.askopenfilename(filetypes=[("Script sources","*.psc *.lua *.txt *.gek *.geck *.obscript *.mwscript"),("All files","*")])
        if not p:return
        try:
            path=Path(p)
            if path.stat().st_size>512*1024:raise ValueError("editor limit: 512 KiB")
            content=path.read_text(encoding="utf-8-sig")
            editor.delete("1.0","end");editor.insert("1.0",content);editor.edit_reset()
            saved.update(path=path,text=content);language.set(language_for(game.get(),p))
            status.set(str(path));schedule()
        except (OSError,ValueError) as exc:messagebox.showerror("Open script",str(exc))
    def save_copy():
        suffix="."+LANGUAGES[language.get()][1][0]
        p=filedialog.asksaveasfilename(defaultextension=suffix)
        if not p:return
        try:
            content=source()
            with Path(p).open("x",encoding="utf-8",newline="\n") as f:f.write(content)
            saved.update(path=Path(p),text=content);status.set("Saved "+p)
        except OSError as exc:messagebox.showerror("Save new copy",str(exc))
    def lint():
        if language.get()!="papyrus":
            report({"scope":"syntax highlighting only for this language; native compiler not integrated"})
            return
        report(check(source()))
    def export_syntax():
        p=filedialog.asksaveasfilename(defaultextension=".sublime-syntax")
        if p:
            try:status.set("Exported "+export(language.get(),p))
            except (OSError,ValueError) as exc:messagebox.showerror("Export syntax",str(exc))
    def compile_script():
        if busy[0]:return
        if language.get()!="papyrus" or saved["path"] is None or saved["text"]!=source():
            messagebox.showinfo("Compile","Select Papyrus and open or save the exact source first.");return
        from .papyrus_build import build, family
        from tkinter import simpledialog
        try:family(game.get())
        except ValueError as exc:messagebox.showerror("Compile",str(exc));return
        backend=simpledialog.askstring("Compiler","Backend: ck or caprica",initialvalue="ck",parent=frame)
        if backend is None:return
        if backend not in ("ck","caprica"):messagebox.showerror("Compiler","Choose ck or caprica");return
        exe=filedialog.askopenfilename(title="Choose trusted installed compiler")
        if not exe:return
        flags=filedialog.askopenfilename(title="Game flags",filetypes=[("Flags","*.flg")])
        if not flags:return
        imports=[]
        while True:
            p=filedialog.askdirectory(title="Choose import directory (Cancel when done)")
            if not p:break
            if p not in imports:imports.append(p)
            if not messagebox.askyesno("Imports","Add another import directory?"):break
        out=filedialog.asksaveasfilename(title="Name a NEW build directory")
        if not out:return
        if not messagebox.askyesno("Run trusted compiler","Execute this local binary? It is not sandboxed."):return
        args=(game.get(),backend,exe,saved["path"],flags,imports,out)
        try:
            if saved["path"].read_text(encoding="utf-8-sig")!=saved["text"]:raise ValueError("Source changed on disk; reopen it before compilation")
        except (OSError,ValueError) as exc:messagebox.showerror("Compile",str(exc));return
        q=queue.Queue();busy[0]=True;status.set("Compiling...")
        def worker():
            try:q.put(build(*args,execute=True))
            except Exception as exc:q.put({"status":"error","message":str(exc)})
        def poll():
            try:r=q.get_nowait()
            except queue.Empty:editor.after(100,poll);return
            busy[0]=False;report(r);status.set(r.get("status","Compiler finished"))
        threading.Thread(target=worker,daemon=True).start();editor.after(100,poll)
    for label,fn in [("Open",open_source),("Save new copy",save_copy),("Check",lint),("Compile Papyrus",compile_script),("Export Sublime syntax",export_syntax)]:
        ttk.Button(bar,text=label,command=fn).pack(side="left")
    def undo(_=None):
        try:editor.edit_undo()
        except tk.TclError:pass
        return "break"
    editor.bind("<Control-z>",undo)
    refresh()
