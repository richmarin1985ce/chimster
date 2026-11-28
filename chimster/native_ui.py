"""Native record workbench; explicit profile, header-derived master order."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
from pathlib import Path
from pprint import pformat
from .native_profiles import PROFILES, capability_manifest, canonical_profile, active_profiles
from .native_parser import parse, subrecords
from .native_editor import NativeSession
from .record_graph import Slots, Identity

def mount(parent, game=None):
    profile=tk.StringVar(value="new-vegas")
    if game is not None:
        def sync(*_):
            try:value=canonical_profile(game.get())
            except ValueError:return
            if value in active_profiles():profile.set(value)
        game.trace_add("write",sync);sync()
    state={"session":None,"source":None,"paths":{},"undo":[],"redo":[]}
    bar=ttk.Frame(parent);bar.pack(fill="x")
    ttk.Combobox(bar,textvariable=profile,values=active_profiles(),state="readonly").pack(side="left")
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
    def open_file(dropped=None):
        name=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Plugins","*.esp *.esm *.esl"),("All","*")])
        if not name:return
        p=Path(name);data=p.read_bytes();kind=profile.get()
        nodes=parse(kind,data)
        if not nodes or nodes[0].signature!=(b"TES3" if kind=="morrowind" else b"TES4"):
            raise ValueError("wrong plugin header")
        masters=[raw.rstrip(b"\0").decode("cp1252") for tag,raw in subrecords(kind,nodes[0]) if tag==b"MAST"]
        s=NativeSession(kind,data,None if kind=="morrowind" else Slots(p.name,masters))
        state.update(session=s,source=p,undo=[],redo=[],master_report=None);refresh()
    def selected():
        if state["session"] is None:raise ValueError("Open a plugin first")
        if not tree.selection():raise ValueError("Select a record first")
        return state["paths"][tree.selection()[0]]
    def inspect():
        s=state["session"];path=selected()
        row=s.rows.get(path)
        show({**row,"editable_fields":s.typed_fields(path)} if row is not None else {"header":s.node(path).header.hex()})
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
        master_report=state.get("master_report")
        if master_report:
            ttk.Button(dialog,text="Master diagnostics",command=lambda:show(master_report)).pack(anchor="w")
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
    def restore_selection(path):
        refresh()
        for item,record_path in state["paths"].items():
            if record_path==path:
                tree.selection_set(item);tree.see(item);inspect();break
    def edit_field():
        path=selected();s=state["session"]
        fields=s.typed_fields(path)
        if not fields:raise ValueError("No supported typed fields on this record")
        revision=s.revision
        dialog=tk.Toplevel(parent);dialog.title("Native property inspector")
        dialog.geometry("620x440")
        ttk.Label(dialog,text=str(s.rows[path]["key"])).pack(anchor="w")
        ttk.Label(dialog,text="Select a property; changes are staged, never written to the source.").pack(anchor="w")
        frame=ttk.Frame(dialog);frame.pack(fill="both",expand=True)
        grid=ttk.Treeview(frame,columns=("field","occurrence","value"),show="tree headings")
        grid.heading("#0",text="Property");grid.column("#0",width=160)
        for col,label,width in (("field","Native field",85),("occurrence","Entry",65),("value","Current value",220)):
            grid.heading(col,text=label);grid.column(col,width=width)
        scroll=ttk.Scrollbar(frame,orient="vertical",command=grid.yview)
        grid.configure(yscrollcommand=scroll.set);scroll.pack(side="right",fill="y");grid.pack(fill="both",expand=True)
        entries={}
        for field in fields:
            values=field["value"] if field["type"]=="properties" else {"value":field["value"]}
            for key,value in values.items():
                item=grid.insert("","end",text=key,values=(field["tag"],field["occurrence"]+1,json.dumps(value,ensure_ascii=False)))
                entries[item]=(field,key,value)
        def apply_property():
            if state["session"] is not s or s.revision!=revision:
                raise ValueError("Property inspector is stale; reopen it")
            if not grid.selection():raise ValueError("Select a property")
            field,key,old_value=entries[grid.selection()[0]]
            # Text is entered literally; numerical and boolean values use JSON.
            value=simpledialog.askstring("Edit "+key,"New value:",initialvalue=old_value if isinstance(old_value,str) else json.dumps(old_value),parent=dialog)
            if value is None:return
            value=value if isinstance(old_value,str) else json.loads(value)
            old=s.data
            s.apply_typed(revision,[(path,field["tag"].encode("ascii"),field["occurrence"],{key:value})])
            if s.data!=old:
                state["undo"].append(old);state["undo"]=state["undo"][-8:];state["redo"].clear()
            dialog.destroy();restore_selection(path)
        ttk.Button(dialog,text="Apply selected property",command=guard(apply_property)).pack(anchor="e")
        grid.bind("<Double-1>",lambda event:guard(apply_property)())

    def remember(old):
        s=state["session"]
        if s.data!=old:
            state["undo"].append(old);state["undo"]=state["undo"][-8:];state["redo"].clear()
    def duplicate_record():
        path=selected();s=state["session"]
        new=simpledialog.askstring("Duplicate record","New Editor ID:",parent=parent)
        if new is None:return
        old=s.data
        if s.profile=="morrowind":
            if len(path)!=1:raise ValueError("Select a named TES3 record")
            identity=s.create_or_duplicate(s.revision,"duplicate",index=path[0],new_id=new)
        else:
            identity=s.create_or_duplicate(s.revision,"native_duplicate",path=path,new_id=new)
        remember(old);restore_selection(s.resolve_identity(identity))
    def create_record():
        s=state["session"]
        if s is None:raise ValueError("Open a plugin first")
        if s.profile not in ("morrowind","new-vegas","fallout3"):
            raise ValueError("Creation templates for this profile are not yet verified")
        editor_id=simpledialog.askstring("Create miscellaneous item","Editor ID:",parent=parent)
        if editor_id is None:return
        name=simpledialog.askstring("Create miscellaneous item","Display name:",parent=parent)
        if name is None:return
        model=simpledialog.askstring("Create miscellaneous item","Relative NIF model path:",parent=parent)
        if model is None:return
        value=simpledialog.askinteger("Create miscellaneous item","Value:",minvalue=0,maxvalue=2147483647,parent=parent)
        if value is None:return
        weight=simpledialog.askfloat("Create miscellaneous item","Weight:",minvalue=0,maxvalue=1000000,parent=parent)
        if weight is None:return
        old=s.data
        if s.profile=="morrowind":
            identity=s.create_or_duplicate(s.revision,"create",signature="MISC",new_id=editor_id,name=name,model=model,properties={"value":value,"weight":weight})
        else:
            identity=s.create_or_duplicate(s.revision,"native_misc",editor_id=editor_id,name=name,model=model,value=value,weight=weight,bounds=[0]*6)
        remember(old);restore_selection(s.resolve_identity(identity))
    def retarget():
        path=selected();s=state["session"];revision=s.revision
        fields=s.reference_fields(path)
        if not fields:raise ValueError("No supported references in selected record")
        dialog=tk.Toplevel(parent);dialog.title("Native reference selector");dialog.geometry("700x480")
        labels=[f'{f["tag"]} #{f["index"]} +{f["offset"]}: {f["target"]}' for f in fields]
        choice=ttk.Combobox(dialog,values=labels,state="readonly");choice.pack(fill="x");choice.current(0)
        query=tk.StringVar()
        ttk.Entry(dialog,textvariable=query).pack(fill="x")
        ttk.Label(dialog,text="Filter by plugin, local ID, record type or Editor ID (first 200 matches).").pack(anchor="w")
        grid=ttk.Treeview(dialog,columns=("origin","id","type","editor"),show="headings")
        for col,label,width in (("origin","Origin plugin",175),("id","Local ID",85),("type","Type",70),("editor","Editor ID",220)):
            grid.heading(col,text=label);grid.column(col,width=width)
        grid.pack(fill="both",expand=True);entries={}
        def populate(*_):
            grid.delete(*grid.get_children());entries.clear()
            f=fields[choice.current()]
            for row in s.reference_targets(path,f["index"],f["offset"],query.get()):
                item=grid.insert("","end",values=(row["origin"],f'{row["local_id"]:06X}',row["signature"],row["editor_id"]))
                entries[item]=row["identity"]
        def apply_target():
            if state["session"] is not s or s.revision!=revision:raise ValueError("Reference selector is stale")
            if not grid.selection():raise ValueError("Select a target")
            from .native_identity import parse_token
            _,target=parse_token(entries[grid.selection()[0]],s.profile)
            f=fields[choice.current()];old=s.data
            s.apply(revision,[(path,f["index"],f["target"],target,f["offset"])])
            remember(old);dialog.destroy();restore_selection(path)
        choice.bind("<<ComboboxSelected>>",populate);query.trace_add("write",populate)
        ttk.Button(dialog,text="Retarget selected reference",command=guard(apply_target)).pack(anchor="e")
        populate()
    def compare_record():
        path=selected();s=state["session"]
        key=s.rows.get(path,{}).get("key")
        if key is None:raise ValueError("Select an identified record")
        name=filedialog.askopenfilename(filetypes=[("Plugins","*.esp *.esm *.esl")])
        if not name:return
        p=Path(name);data=p.read_bytes();nodes=parse(s.profile,data)
        masters=[raw.rstrip(bytes(1)).decode("cp1252") for tag,raw in subrecords(s.profile,nodes[0]) if tag==b"MAST"]
        other=NativeSession(s.profile,data,None if s.slots is None else Slots(p.name,masters))
        matches=other.paths.get(key,())
        if len(matches)!=1:raise ValueError("Same persistent record identity not uniquely found")
        from .native_compare import semantic_compare
        report=semantic_compare(s.profile,s.data,path,s.slots,data,matches[0],other.slots)
        dialog=tk.Toplevel(parent);dialog.title("Record conflict comparison");dialog.geometry("800x480")
        ttk.Label(dialog,text=str(key)+" | "+report["semantic_coverage"]).pack(anchor="w")
        grid=ttk.Treeview(dialog,columns=("status","left","right"),show="tree headings")
        grid.heading("#0",text="Field / occurrence");grid.column("#0",width=130)
        for col in ("status","left","right"):grid.heading(col,text=col.title());grid.column(col,width=175)
        for row in report["fields"]:
            def value(side):
                item=row[side]
                return "" if item is None else item["preview"]
            grid.insert("","end",text=f'{row["tag"]} #{row["occurrence"]+1}',values=(row.get("semantic_status",row["status"]),value("left"),value("right")))
        grid.pack(fill="both",expand=True)
        ttk.Label(dialog,text="Opaque fields are not safe to merge automatically.").pack(anchor="w")

    def string_table():
        from .compatibility_strings import parse as parse_table,edit as edit_table
        from hashlib import sha256
        name=filedialog.askopenfilename(filetypes=[("Native string tables","*.strings *.dlstrings *.ilstrings")])
        if not name:return
        p=Path(name);kind=p.suffix[1:].upper()
        encoding=simpledialog.askstring("String table encoding","Encoding:",initialvalue="utf-8",parent=parent)
        if encoding is None:return
        data=p.read_bytes();original=parse_table(data,kind,encoding);changes={}
        dialog=tk.Toplevel(parent);dialog.title("Native string table: "+p.name);dialog.geometry("720x500")
        query=tk.StringVar();ttk.Entry(dialog,textvariable=query).pack(fill="x")
        grid=ttk.Treeview(dialog,columns=("value",),show="tree headings")
        grid.heading("#0",text="String ID");grid.heading("value",text="Text")
        grid.column("#0",width=110);grid.column("value",width=530);grid.pack(fill="both",expand=True)
        entries={}
        def populate(*_):
            grid.delete(*grid.get_children());entries.clear();q=query.get().casefold()
            for key,value in original.items():
                value=changes.get(key,value)
                if q not in f"{key} {value}".casefold():continue
                item=grid.insert("","end",text=str(key),values=(value,));entries[item]=key
                if len(entries)>=500:break
        def modify():
            if not grid.selection():raise ValueError("Select a string ID")
            key=entries[grid.selection()[0]]
            value=simpledialog.askstring("Edit string "+str(key),"New text:",initialvalue=changes.get(key,original[key]),parent=dialog)
            if value is None:return
            if value==original[key]:changes.pop(key,None)
            else:
                value.encode(encoding)
                if chr(0) in value:raise ValueError("Embedded null")
                changes[key]=value
            populate()
        def save_table():
            if not changes:raise ValueError("No changes to export")
            directory=filedialog.askdirectory(title="Choose staging directory")
            if not directory:return
            output=Path(directory)/p.name
            result=edit_table(data,kind,changes,sha256(data).hexdigest(),encoding)
            with output.open("xb") as stream:stream.write(result)
            messagebox.showinfo("Native strings",f"Exported {len(changes)} changed strings to {output}",parent=dialog)
        ttk.Label(dialog,text="Filter by ID or text; first 500 matches. Original table is never overwritten.").pack(anchor="w")
        ttk.Button(dialog,text="Edit string",command=guard(modify)).pack(anchor="e")
        ttk.Button(dialog,text="Export staged table",command=guard(save_table)).pack(anchor="e")
        grid.bind("<Double-1>",lambda event:guard(modify)());query.trace_add("write",populate);populate()
    def history(reverse):
        s=state["session"]
        if s is None:raise ValueError("Open a plugin first")
        source="redo" if reverse else "undo";destination="undo" if reverse else "redo"
        if not state[source]:raise ValueError("No history in that direction")
        path=selected() if tree.selection() else ()
        candidate=NativeSession(s.profile,state[source][-1],s.slots,s.external_types,s.external_records)
        state[source].pop();state[destination].append(s.data);state["session"]=candidate
        restore_selection(path)
    def export():
        s=state["session"];source=state["source"]
        if s is None:raise ValueError("Open a plugin first")
        directory=filedialog.askdirectory(title="Choose staging directory")
        if not directory:return
        target=Path(directory)/source.name
        from .native_save import save
        save(s.profile,s.data,target)
        show({"export":str(target),"revision":s.revision})
    ttk.Button(bar,text="Capabilities",command=guard(lambda:show(capability_manifest()))).pack(side="left")
    ttk.Button(bar,text="Open plugin",command=guard(open_file)).pack(side="left")
    ttk.Button(bar,text="Dependencies",command=guard(lambda:review(False))).pack(side="left")
    ttk.Button(bar,text="Dependents",command=guard(lambda:review(True))).pack(side="left")
    ttk.Button(bar,text="Load masters",command=guard(load_masters)).pack(side="left")
    ttk.Button(bar,text="Validate",command=guard(validate)).pack(side="left")
    ttk.Button(bar,text="Edit typed field",command=guard(edit_field)).pack(side="left")
    actions=ttk.Frame(parent);actions.pack(fill="x",before=pane)
    ttk.Button(actions,text="Native strings",command=guard(string_table)).pack(side="left")
    ttk.Button(actions,text="New item",command=guard(create_record)).pack(side="left")
    ttk.Button(actions,text="Duplicate",command=guard(duplicate_record)).pack(side="left")
    ttk.Button(actions,text="Retarget",command=guard(retarget)).pack(side="left")
    ttk.Button(actions,text="Compare",command=guard(compare_record)).pack(side="left")
    ttk.Button(actions,text="Undo",command=guard(lambda:history(False))).pack(side="left")
    ttk.Button(actions,text="Redo",command=guard(lambda:history(True))).pack(side="left")
    ttk.Button(actions,text="Export staged copy",command=guard(export)).pack(side="left")
    tree.bind("<<TreeviewSelect>>",lambda event:guard(inspect)() if tree.selection() else None)
    from .drop_import import editor_drop
    editor_drop(parent,[([".esp",".esm",".esl"],open_file,False)])
