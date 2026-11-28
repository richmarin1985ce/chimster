"""Shared project dashboard. All mutation is explicit and revision checked."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from .project import Project,KINDS
def mount(parent,game):
    current=None;revision=None
    from .editor_presence import Presence
    presence=None
    try:presence=Presence()
    except (OSError,ValueError):pass
    def close_presence(event):
        if event.widget is parent and presence:
            try:presence.close()
            except OSError:pass
    parent.bind("<Destroy>",close_presence,add="+")
    label=tk.StringVar(value="Create or open a local project.")
    ttk.Label(parent,textvariable=label,wraplength=900).pack(fill="x")
    table=ttk.Treeview(parent,columns=("kind","filename","size"),show="tree headings",selectmode="browse")
    table.heading("#0",text="Artifact ID")
    for k in ("kind","filename","size"):table.heading(k,text=k.capitalize())
    table.column("#0",width=180);table.column("kind",width=120);table.column("filename",width=300);table.column("size",width=90)
    table.pack(fill="both",expand=True)
    bar=ttk.Frame(parent);bar.pack(fill="x")
    def refresh():
        nonlocal revision
        if not current:return
        m=current.read();revision=m["revision"];game.set(m["game"])
        label.set(f'{m["name"]} | {m["game"]} | revision {revision} | {current.root}')
        previous=table.selection()
        table.delete(*table.get_children())
        for k,a in sorted(m["artifacts"].items()):table.insert("","end",iid=k,text=k,values=(a["kind"],a["filename"],a["size"]))
        if previous and table.exists(previous[0]):table.selection_set(previous[0])
    def heartbeat():
        if current:
            try:
                if current.read()["revision"]!=revision:refresh()
                selection=table.selection()
                if presence:presence.publish(current,selection[0] if selection else None)
            except (OSError,ValueError,KeyError,TypeError):pass
        parent.after(3000,heartbeat)
    parent.after(0,heartbeat)
    def guard(fn):
        def wrapped():
            try:fn()
            except (OSError,ValueError,KeyError,TypeError) as e:messagebox.showerror("Project",str(e))
        return wrapped
    def create():
        nonlocal current
        d=filedialog.askdirectory(title="Choose project folder")
        if not d:return
        n=simpledialog.askstring("Project","Project ID",initialvalue=Path(d).name)
        if n:current=Project.create(d,n,game.get());refresh()
    def open_project(dropped=None):
        nonlocal current
        d=dropped if dropped is not None else filedialog.askdirectory(title="Open project")
        if d:current=Project(d);refresh()
    def selected():
        s=table.selection()
        if not current or not s:raise ValueError("select an artifact")
        return s[0]
    def add(dropped=None):
        if not current:raise ValueError("open a project first")
        p=dropped if dropped is not None else filedialog.askopenfilename()
        if not p:return
        k=simpledialog.askstring("Artifact","Stable artifact ID",initialvalue=Path(p).stem)
        if not k:return
        kind=simpledialog.askstring("Artifact kind",", ".join(sorted(KINDS)),initialvalue="other")
        if not kind:return
        exists=k in current.read()["artifacts"]
        if exists and not messagebox.askyesno("Replace artifact","Create a new revision of this artifact?"):return
        current.add(k,kind,p,revision,exists);refresh()
    def export():
        k=selected();a=current.read()["artifacts"][k]
        p=filedialog.asksaveasfilename(initialfile=a["filename"])
        if p:current.export(k,p)
    def remove():
        k=selected()
        if messagebox.askyesno("Remove","Remove this artifact from the current revision? Older revisions retain it."):
            current.remove(k,revision);refresh()
    def rollback():
        if not current:raise ValueError("open a project first")
        n=simpledialog.askinteger("Rollback","Revision to restore as a new revision",minvalue=0,maxvalue=revision)
        if n is not None and n!=revision and messagebox.askyesno("Confirm rollback",f"Restore revision {n} as a new revision? Current history is retained."):
            current.rollback(n,revision);refresh()
    def verify():
        if not current:raise ValueError("open a project first")
        r=current.verify();messagebox.showinfo("Project integrity",str(r))
    def build():
        k=selected();a=current.read()["artifacts"][k];kind=a["kind"]
        if kind not in {"quest","records"}:raise ValueError("select a native quest or records JSON artifact")
        output=simpledialog.askstring("Build","Output artifact ID")
        if not output:return
        name=simpledialog.askstring("Build","ESP filename",initialvalue=output+".esp")
        if not name:return
        raw=simpledialog.askstring("Build","Master artifact IDs, in order, separated by commas (blank for none)")
        if raw is None:return
        draft=kind=="quest" and messagebox.askyesno("Script draft","Allow uncompiled quest script source? Drafts must not be used in game.")
        from .project_build import build as compile_project
        r=compile_project(current,kind,k,output,name,revision,[v.strip() for v in raw.split(",") if v.strip()],draft)
        refresh();messagebox.showinfo("Build",str(r))
    for t,fn in (("New",create),("Open",open_project),("Refresh",refresh),("Import",add),("Export",export),("Remove",remove),("Rollback",rollback),("Verify",verify),("Build plugin",build)):
        ttk.Button(bar,text=t,command=guard(fn)).pack(side="left")
    from .drop_import import editor_drop
    editor_drop(parent,[(["<directory>"],open_project,False),([".esp",".esm",".esl",".json",".nif",".dds",".psc",".wav",".fuz",".obj",".xml"],add,False)])
