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
        if language.get()=="papyrus":report(check(source()));return
        if language.get() in ("geck","oblivion","morrowind"):
            from .legacy_compile import lint as legacy_lint
            from .script_syntax import PROFILE
            if PROFILE.get(game.get())!=language.get():
                status.set("Select matching legacy game profile");return
            report(legacy_lint(source(),game.get()));return
        report({"scope":"Use Lua check with a locally installed Lua 5.1 compiler"})
    # Explicit extender opt-in: API availability is not inferred from game files.
    from .script_symbols import complete, lookup, index_papyrus_library
    from dataclasses import asdict
    import re
    extender = tk.StringVar(value="")
    library = {"game":None,"symbols":()}
    api_bar = ttk.Frame(frame); api_bar.pack(fill="x",before=pane)
    ttk.Label(api_bar,text="API extension").pack(side="left")
    ttk.Combobox(api_bar,textvariable=extender,values=["","skse","f4se","obse","fose","xnvse"],state="readonly",width=10).pack(side="left")
    def symbol_prefix():
        before=editor.get("insert linestart","insert")
        match=re.search(r"([A-Za-z_][A-Za-z0-9_]*)$",before)
        prefix=match.group(1) if match else ""
        return prefix
    def enabled():
        return [extender.get()] if extender.get() else []
    def current_library():
        return library["symbols"] if language.get()=="papyrus" and library["game"]==game.get() else ()
    def load_library():
        if language.get()!="papyrus":
            status.set("Library indexing is available for Papyrus");return
        root=filedialog.askdirectory(title="Select local Papyrus source library")
        if not root:return
        target=game.get()
        try:
            result=index_papyrus_library(root)
            library.update(game=target,symbols=result["symbols"])
            report({k:v for k,v in result.items() if k!="symbols"} | {"symbols":len(result["symbols"]),"game":target})
            status.set("Indexed %d symbols"%len(result["symbols"]))
        except (ValueError,OSError) as exc:messagebox.showerror("Index library",str(exc))
    def suggest(_=None):
        prefix=symbol_prefix()
        try:items=complete(game.get(),language.get(),source(),prefix,enabled(),library=current_library())
        except ValueError as exc:status.set(str(exc));return "break"
        if not items:status.set("No known symbols");return "break"
        popup=tk.Toplevel(frame);popup.title("Script completions");popup.transient(frame.winfo_toplevel())
        listing=tk.Listbox(popup,width=85,height=min(12,len(items)),exportselection=False)
        listing.pack(fill="both",expand=True)
        for s in items:listing.insert("end",f"{s.name}   {s.owner}   [{s.origin}]   {s.signature}")
        listing.selection_set(0);listing.focus_set()
        # Do not insert into a changed source or at a moved cursor.
        initial=source();index=editor.index("insert")
        def choose(_=None):
            if listing.curselection():
                s=items[listing.curselection()[0]]
                if source()==initial and editor.index("insert")==index:
                    editor.edit_separator()
                    if prefix:editor.delete("insert-%dc"%len(prefix),"insert")
                    editor.insert("insert",s.name);editor.edit_separator()
                    report(asdict(s))
            popup.destroy();editor.focus_set()
        listing.bind("<Return>",choose);listing.bind("<Double-Button-1>",choose)
        listing.bind("<Escape>",lambda _:popup.destroy())
        ttk.Button(popup,text="Insert selected symbol",command=choose).pack(fill="x")
        return "break"
    def symbol_help(_=None):
        before=editor.get("insert linestart","insert")
        after=editor.get("insert","insert lineend")
        a=re.search(r"[A-Za-z_][A-Za-z0-9_]*$",before)
        b=re.match(r"[A-Za-z0-9_]+",after)
        name=(a.group() if a else "")+(b.group() if b else "")
        if not name:status.set("Place cursor on a symbol");return "break"
        try:items=lookup(game.get(),language.get(),source(),name,enabled(),library=current_library())
        except ValueError as exc:status.set(str(exc));return "break"
        report({"symbol":name,"matches":[asdict(s) for s in items],
                "scope":"advisory seed catalog and current source; unknown is not an error"})
        if len(items)==1 and items[0].origin=="local" and items[0].line:
            editor.mark_set("insert",f"{items[0].line}.0");editor.see("insert")
        return "break"
    ttk.Button(api_bar,text="Index local PSC",command=load_library).pack(side="left")
    ttk.Button(api_bar,text="Complete (Ctrl+Space)",command=suggest).pack(side="left")
    ttk.Button(api_bar,text="Symbol help / definition (F12)",command=symbol_help).pack(side="left")
    editor.bind("<Control-space>",suggest)
    editor.bind("<F12>",symbol_help)
    def export_syntax():
        p=filedialog.asksaveasfilename(defaultextension=".sublime-syntax")
        if p:
            try:status.set("Exported "+export(language.get(),p))
            except (OSError,ValueError) as exc:messagebox.showerror("Export syntax",str(exc))
    diagnostic_items=[]
    def show_build(r):
        from .compiler_diagnostics import collect,summarize
        diagnostic_items[:]=collect(r)
        report({**r,"diagnostic_summary":summarize(diagnostic_items)})
    def jump_diagnostic():
        from .compiler_diagnostics import navigation
        if saved["path"] is None or saved["text"]!=source():
            status.set("Open the unchanged source before navigating diagnostics");return
        from .papyrus_build import digest
        try:
            current_hash=digest(saved["path"])
            if saved["path"].read_text(encoding="utf-8-sig")!=saved["text"]:raise ValueError("Source changed on disk")
        except (OSError,ValueError) as exc:status.set(str(exc));return
        matches=[(item,navigation(item,saved["path"],source())) for item in diagnostic_items
                 if not item.get("source_sha256") or item["source_sha256"]==current_hash]
        matches=[(item,index) for item,index in matches if index]
        if not matches:status.set("No diagnostics for the current saved file");return
        popup=tk.Toplevel(frame);popup.title("Compiler diagnostics")
        listing=tk.Listbox(popup,width=100,height=min(15,len(matches)));listing.pack(fill="both",expand=True)
        for item,index in matches:listing.insert("end",f"{item['severity']} | line {item['line']} | {item['message']}")
        listing.selection_set(0)
        def choose(_=None):
            if listing.curselection():
                index=matches[listing.curselection()[0]][1]
                editor.mark_set("insert",index);editor.see(index);editor.focus_set()
            popup.destroy()
        listing.bind("<Return>",choose);listing.bind("<Double-Button-1>",choose)
        ttk.Button(popup,text="Go to line",command=choose).pack(fill="x")
    def check_lua():
        if busy[0]:return
        if game.get()!="openmw" or language.get()!="lua" or saved["path"] is None or saved["text"]!=source():
            status.set("Select OpenMW and save the unchanged Lua source first");return
        from .lua_compile import check as lua_check
        exe=filedialog.askopenfilename(title="Choose trusted installed Lua 5.1 compiler")
        if not exe or not messagebox.askyesno("Run compiler","Execute the selected trusted compiler? Source will be parsed, not run."):return
        try:
            if saved["path"].read_text(encoding="utf-8-sig")!=saved["text"]:raise ValueError("Source changed on disk")
        except (OSError,ValueError) as exc:messagebox.showerror("Lua check",str(exc));return
        path=saved["path"];q=queue.Queue();busy[0]=True
        def worker():
            try:q.put(lua_check(exe,path,execute=True))
            except Exception as exc:q.put({"status":"error","message":str(exc)})
        def poll():
            try:r=q.get_nowait()
            except queue.Empty:editor.after(100,poll);return
            busy[0]=False;show_build(r);status.set(r.get("status","Lua check complete"))
        threading.Thread(target=worker,daemon=True).start();editor.after(100,poll)
    def recover_script():
        if busy[0]:return
        from .pex_decompile import decompile
        from .papyrus_build import family
        try:family(game.get())
        except ValueError as exc:status.set(str(exc));return
        src=filedialog.askopenfilename(title="Choose PEX you have rights to inspect",filetypes=[("Compiled scripts","*.pex")])
        if not src:return
        exe=filedialog.askopenfilename(title="Choose trusted installed Champollion")
        if not exe:return
        out=filedialog.asksaveasfilename(title="Name a NEW recovery directory")
        if not out:return
        if not messagebox.askyesno("Run trusted decompiler","Recover source using this unsandboxed local tool?"):return
        target=game.get();q=queue.Queue();busy[0]=True;status.set("Recovering source...")
        def worker():
            try:q.put(decompile(target,exe,src,out,execute=True))
            except Exception as exc:q.put({"status":"error","message":str(exc)})
        def poll():
            try:r=q.get_nowait()
            except queue.Empty:editor.after(100,poll);return
            busy[0]=False;show_build(r);status.set(r.get("status","Recovery complete"))
        threading.Thread(target=worker,daemon=True).start();editor.after(100,poll)
    def compile_script(project=False):
        if busy[0]:return
        if language.get()!="papyrus" or (not project and (saved["path"] is None or saved["text"]!=source())):
            messagebox.showinfo("Compile","Select Papyrus and open or save the exact source first.");return
        from .papyrus_build import build, family
        from .papyrus_batch import batch
        from tkinter import simpledialog
        try:family(game.get())
        except ValueError as exc:messagebox.showerror("Compile",str(exc));return
        if project:
            if source()!=saved["text"] and source() and not messagebox.askyesno("Unsaved editor changes","Batch uses saved files on disk only. Continue?"):return
            target=filedialog.askdirectory(title="Select flat project PSC directory")
            if not target:return
        else:target=saved["path"]
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
        reuse=None
        if project and messagebox.askyesno("Reuse build","Try an unchanged prior local build?"):
            reuse=filedialog.askdirectory(title="Choose completed build directory") or None
        args=(game.get(),backend,exe,target,flags,imports,out)
        try:
            if not project and saved["path"].read_text(encoding="utf-8-sig")!=saved["text"]:raise ValueError("Source changed on disk; reopen it before compilation")
        except (OSError,ValueError) as exc:messagebox.showerror("Compile",str(exc));return
        q=queue.Queue();busy[0]=True;status.set("Compiling...")
        def worker():
            try:q.put(batch(*args,execute=True,reuse=reuse) if project else build(*args,execute=True))
            except Exception as exc:q.put({"status":"error","message":str(exc)})
        def poll():
            try:r=q.get_nowait()
            except queue.Empty:editor.after(100,poll);return
            busy[0]=False;show_build(r);status.set(r.get("status","Compiler finished"))
        threading.Thread(target=worker,daemon=True).start();editor.after(100,poll)
    compiler_bar=ttk.Frame(frame);compiler_bar.pack(fill="x",before=pane)
    def run_tool(action):
        if busy[0]:return
        q=queue.Queue();busy[0]=True;status.set("Working...")
        def worker():
            try:q.put(action())
            except Exception as exc:q.put({"status":"error","message":str(exc)})
        def poll():
            try:r=q.get_nowait()
            except queue.Empty:editor.after(100,poll);return
            busy[0]=False;show_build(r);status.set(r.get("status","Finished"))
        threading.Thread(target=worker,daemon=True).start();editor.after(100,poll)
    def discover_compiler():
        from .compiler_profiles import discover
        target=game.get()
        root=filedialog.askdirectory(title="Choose game install directory (Cancel searches PATH)")
        try:report(discover(target,root or None))
        except (OSError,ValueError) as exc:messagebox.showerror("Compiler discovery",str(exc))
    def profile_build():
        if busy[0]:return
        from .compiler_profiles import load,configured_build
        cfg=filedialog.askopenfilename(title="Select trusted local compiler profile",filetypes=[("JSON","*.json")])
        if not cfg:return
        try:
            settings=load(cfg)
            if settings["game"]!=game.get():raise ValueError("Profile game does not match selected game")
        except (OSError,ValueError,KeyError,TypeError) as exc:messagebox.showerror("Compiler profile",str(exc));return
        project=messagebox.askyesno("Build type","Build an entire flat source directory? No selects a saved script.")
        if project:
            source_path=filedialog.askdirectory(title="Select saved PSC project directory")
        else:
            if saved["path"] is None or saved["text"]!=source() or language.get()!="papyrus":
                status.set("Open or save unchanged Papyrus source first");return
            source_path=saved["path"]
            try:
                if source_path.read_text(encoding="utf-8-sig")!=saved["text"]:raise ValueError("Source changed on disk")
            except (OSError,ValueError) as exc:messagebox.showerror("Compiler profile",str(exc));return
        if not source_path:return
        output_path=filedialog.asksaveasfilename(title="Name a NEW output directory")
        if not output_path:return
        if not messagebox.askyesno("Execute compiler",f"Run trusted local compiler? It is not sandboxed.\n{settings['compiler']}"):return
        run_tool(lambda:configured_build(cfg,source_path,output_path,project=project,execute=True))
    def runtime_log():
        from .papyrus_runtime import inspect
        path=filedialog.askopenfilename(title="Choose local Papyrus runtime log",filetypes=[("Logs","*.log *.txt"),("All files","*")])
        if path:run_tool(lambda:inspect(path))
    def legacy_handoff():
        if busy[0]:return
        from .legacy_compile import PROFILES,inspect,prepare,attach
        from tkinter import simpledialog
        target=game.get()
        if target not in PROFILES:status.set("Select a legacy game");return
        action=simpledialog.askstring("Legacy script handoff","inspect, prepare or attach?",initialvalue="inspect",parent=frame)
        if action not in ("inspect","prepare","attach"):return
        plugin=filedialog.askopenfilename(title="Select original or draft plugin",filetypes=[("Plugins","*.esp *.esm")])
        if not plugin:return
        if action=="inspect":run_tool(lambda:inspect(plugin,target));return
        folder=filedialog.askdirectory(title="Choose separate output directory")
        if not folder:return
        destination=Path(folder)/Path(plugin).name
        if action=="prepare":
            ident=simpledialog.askstring("Script identity","Script name" if target=="morrowind" else "Disk FormID (0x...)",parent=frame)
            if not ident:return
            src=filedialog.askopenfilename(title="Select saved UTF-8 script source")
            if not src:return
            if not messagebox.askyesno("Uncompiled draft","Create an uncompiled draft for the native editor? Do not load it in a game."):return
            run_tool(lambda:prepare(plugin,destination,target,ident,src))
        else:
            donor=filedialog.askopenfilename(title="Select same-name compiled donor plugin")
            if donor:run_tool(lambda:attach(plugin,donor,destination,target))
    for label,fn in [("Discover compiler",discover_compiler),("Build with profile",profile_build),
                     ("Legacy handoff",legacy_handoff),("Runtime log",runtime_log)]:
        ttk.Button(compiler_bar,text=label,command=fn).pack(side="left")
    ttk.Button(api_bar,text="Recover PEX",command=recover_script).pack(side="left")
    ttk.Button(api_bar,text="Diagnostics",command=jump_diagnostic).pack(side="left")
    ttk.Button(api_bar,text="Lua check",command=check_lua).pack(side="left")
    ttk.Button(api_bar,text="Build project",command=lambda:compile_script(True)).pack(side="left")
    for label,fn in [("Open",open_source),("Save new copy",save_copy),("Check",lint),("Compile Papyrus",compile_script),("Export Sublime syntax",export_syntax)]:
        ttk.Button(bar,text=label,command=fn).pack(side="left")
    def undo(_=None):
        try:editor.edit_undo()
        except tk.TclError:pass
        return "break"
    editor.bind("<Control-z>",undo)
    refresh()
