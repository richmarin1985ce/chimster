"""Native record workbench; explicit profile, header-derived master order."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from pprint import pformat
from .native_profiles import PROFILES, capability_manifest
from .native_parser import parse, subrecords
from .native_editor import NativeSession
from .record_graph import Slots, Identity

def mount(parent, game=None):
    aliases={"newvegas":"new-vegas","skyrimse":"skyrim-se","oblivionremastered":"oblivion-remastered"}
    profile=tk.StringVar(value=aliases.get(game.get(),game.get()) if game is not None else "new-vegas")
    if game is not None:
        def sync(*_):
            value=aliases.get(game.get(),game.get())
            if value in PROFILES:profile.set(value)
        game.trace_add("write",sync)
    state={"session":None,"source":None,"paths":{},"undo":[],"redo":[]}
    bar=ttk.Frame(parent);bar.pack(fill="x")
    ttk.Combobox(bar,textvariable=profile,values=list(PROFILES),state="readonly").pack(side="left")
    pane=ttk.Panedwindow(parent,orient="horizontal");pane.pack(fill="both",expand=True)
    left=ttk.Frame(pane);right=ttk.Frame(pane);pane.add(left,weight=1);pane.add(right,weight=2)
    tree=ttk.Treeview(left,show="tree")
    scroll=ttk.Scrollbar(left,orient="vertical",command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right",fill="y");tree.pack(fill="both",expand=True)
    out=tk.Text(right,wrap="word",state="disabled")
    detail_scroll=ttk.Scrollbar(right,orient="vertical",command=out.yview)
    out.configure(yscrollcommand=detail_scroll.set)
    detail_scroll.pack(side="right",fill="y");out.pack(fill="both",expand=True)
    def show(value):
        out.configure(state="normal")
        out.delete("1.0","end");out.insert("1.0",pformat(value))
        out.configure(state="disabled")
    def guard(fn):
        def run():
            try:fn()
            except (OSError,ValueError,KeyError,IndexError,TypeError) as exc:
                messagebox.showerror("Native records",str(exc))
        return run
    def refresh():
        tree.delete(*tree.get_children());state["paths"].clear()
        s=state["session"]
        def walk(nodes,parent="",prefix=()):
            for i,n in enumerate(nodes):
                path=prefix+(i,)
                row=s.rows.get(path,{})
                item=tree.insert(parent,"end",text=n.signature.decode("ascii",errors="replace")+" "+str(row.get("key","")))
                state["paths"][item]=path
                walk(n.children,item,path)
        walk(s.nodes)
    def open_file():
        name=filedialog.askopenfilename(filetypes=[("Plugins","*.esp *.esm *.esl"),("All","*")])
        if not name:return
        p=Path(name);data=p.read_bytes();kind=profile.get()
        nodes=parse(kind,data)
        if not nodes or nodes[0].signature!=(b"TES3" if kind=="morrowind" else b"TES4"):
            raise ValueError("wrong plugin header")
        masters=[raw.rstrip(b"\0").decode("cp1252") for tag,raw in subrecords(kind,nodes[0]) if tag==b"MAST"]
        s=NativeSession(kind,data,None if kind=="morrowind" else Slots(p.name,masters))
        state.update(session=s,source=p,undo=[],redo=[],master_report=None);refresh()
    def selected():
        if not tree.selection():raise ValueError("Select a record first")
        return state["paths"][tree.selection()[0]]
    def inspect():
        s=state["session"];path=selected()
        row=s.rows.get(path)
        show(row if row is not None else {"header":s.node(path).header.hex()})
    def review(reverse):
        path=selected();s=state["session"]
        key=s.rows.get(path,{}).get("key")
        if key is None:raise ValueError("no persistent identity")
        show(s.review(key,reverse))
    def validate():
        s=state["session"]
        if s is None:raise ValueError("Open a plugin first")
        report=s.validation_summary()
        dialog=tk.Toplevel(parent)
        dialog.title("Native validation")
        ttk.Label(dialog,text=f'{s.profile}: {report["records"]} records, {len(report["issues"])} diagnostics').pack(anchor="w")
        choice=tk.StringVar(value="All")
        ttk.Combobox(dialog,textvariable=choice,state="readonly",values=["All","Errors","Warnings",*sorted(report["counts"])]).pack(fill="x")
        frame=ttk.Frame(dialog);frame.pack(fill="both",expand=True)
        results=ttk.Treeview(frame,columns=("severity","detail"),show="tree headings")
        results.heading("#0",text="Diagnostic")
        results.heading("severity",text="Severity")
        results.column("severity",width=90,stretch=False)
        results.heading("detail",text="Details")
        scroll=ttk.Scrollbar(frame,orient="vertical",command=results.yview)
        results.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right",fill="y");results.pack(fill="both",expand=True)
        entries={}
        def populate(*_):
            results.delete(*results.get_children());entries.clear()
            for issue in report["issues"]:
                severity=s.diagnostic_severity(issue[0])
                if choice.get() not in ("All",issue[0],severity.title()+"s"):continue
                item=results.insert("","end",text=issue[0],values=(severity,str(issue[1:])))
                entries[item]=issue
        def navigate():
            if state["session"] is not s or s.revision!=report["revision"]:
                raise ValueError("Validation report is stale; run validation again")
            if not results.selection():return
            issue=entries[results.selection()[0]]
            path=issue[2][0] if issue[0]=="duplicate-identity" else issue[1]
            for item,record_path in state["paths"].items():
                if record_path==path:
                    tree.selection_set(item);tree.see(item);inspect();return
        choice.trace_add("write",populate)
        ttk.Button(dialog,text="Go to record",command=guard(navigate)).pack(anchor="w")
        results.bind("<Double-1>",lambda event:guard(navigate)())
        ttk.Label(dialog,text="Incomplete schemas are coverage warnings, not proof of corruption.").pack(anchor="w")
        if state.get("master_report"):
            ttk.Button(dialog,text="Master diagnostics",command=lambda:show(state["master_report"])).pack(anchor="w")
        populate()
    def load_masters():
        s=state["session"]
        if s is None:raise ValueError("Open a plugin first")
        if s.slots is None:raise ValueError("TES3 master indexing not supported yet")
        directory=filedialog.askdirectory(title="Choose plugin master directory")
        if not directory:return
        from .native_master_index import index_masters
        types,report=index_masters(s.profile,Path(directory),s.slots.names[:-1])
        candidate=NativeSession(s.profile,s.data,s.slots,types,report.pop("records",{}))
        state["session"]=candidate
        state["master_report"]=report
        refresh()
        show({"master_index":report,"external_types":len(types),"diagnostics":candidate.validate()})
    def export():
        s=state["session"];source=state["source"]
        if s is None:raise ValueError("Open a plugin first")
        directory=filedialog.askdirectory(title="Choose staging directory")
        if not directory:return
        target=Path(directory)/source.name
        with target.open("xb") as f:f.write(s.data)
        show({"export":str(target),"revision":s.revision})
    ttk.Button(bar,text="Capabilities",command=guard(lambda:show(capability_manifest()))).pack(side="left")
    ttk.Button(bar,text="Open plugin",command=guard(open_file)).pack(side="left")
    ttk.Button(bar,text="Dependencies",command=guard(lambda:review(False))).pack(side="left")
    ttk.Button(bar,text="Dependents",command=guard(lambda:review(True))).pack(side="left")
    ttk.Button(bar,text="Load masters",command=guard(load_masters)).pack(side="left")
    ttk.Button(bar,text="Validate",command=guard(validate)).pack(side="left")
    ttk.Button(bar,text="Export staged copy",command=guard(export)).pack(side="left")
    tree.bind("<<TreeviewSelect>>",lambda event:guard(inspect)() if tree.selection() else None)
