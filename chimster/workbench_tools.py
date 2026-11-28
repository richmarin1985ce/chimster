"""Desktop access to existing CLI commands; no shell evaluation."""
import sys, subprocess, threading, queue, json
import tkinter as tk
from tkinter import ttk, messagebox

GROUPS={
"Core":("dependencies","project","extension-info"),
"Compatibility":("compatibility","tes3-inventory"),
"Records":("fnv-index","record-compare","record-build","master-reorder"),
"Mod management":("loadorder","install-zip","fomod","stage-overlay","autopatch"),
"World":("fnv-world","fnv-interior","navmesh-auto","navmesh-route","navmesh-draft","building","chunk-build","chunk-load"),
"Landscape":("landscape-budget","terrain-tile"),
"Validation":("world-check","audit-assets","interior-check"),
"Rendering":("render-preview","render-benchmark"),
"Meshes":("flora","native-flora","modern-nif"),
"Collision":("collision-box","interior-check"),
"Textures":("texture-compress","texture-height-alpha","textures"),
"LOD":("lod",),
"Version control":("git-history","git-branches","record-compare"),
"Quests":("quest-check","quest-states","quest-native","quest-scenes","dialogue-view-generate"),
"Scripting":("script-check","quest-scripts","quest-attach-scripts"),
"Books":("book","book-layout"),
"Characters":("record-build","record-inspect","record-edit"),
"Gameplay":("fnv-gmst-patch","record-build"),
"Audio":(),
"Localization":("localize","localization-audit"),
"Interfaces":("minigame","ffdec"),
"Testing":("render-benchmark","world-check","wiki-check-links"),
"AI":("plan","knowledge","local-ai"),
"Wiki":("wiki","wiki-export","wiki-check-links"),
"Distribution":("app-release","extension-info"),
"Expansion projects":("flagstaff",),
}
def mount(parent):
    import argparse
    from tkinter import filedialog
    from .cli import build_parser
    parser=build_parser()
    commands=next(a for a in parser._actions if isinstance(a,argparse._SubParsersAction)).choices
    area=tk.StringVar(value="Records");command=tk.StringVar()
    bar=ttk.Frame(parent);bar.pack(fill="x")
    ttk.Combobox(bar,textvariable=area,values=list(GROUPS),state="readonly").pack(side="left")
    choices=ttk.Combobox(bar,textvariable=command,state="readonly");choices.pack(side="left",fill="x",expand=True)
    holder=ttk.Frame(parent);holder.pack(fill="both",expand=True)
    canvas=tk.Canvas(holder,height=240,highlightthickness=0);canvas.pack(side="left",fill="both",expand=True)
    scroll=ttk.Scrollbar(holder,orient="vertical",command=canvas.yview);scroll.pack(side="right",fill="y")
    canvas.configure(yscrollcommand=scroll.set)
    form=ttk.Frame(canvas);window=canvas.create_window((0,0),window=form,anchor="nw")
    form.bind("<Configure>",lambda e:canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",lambda e:canvas.itemconfigure(window,width=e.width))
    out=tk.Text(parent,height=12,wrap="word");out.pack(fill="both",expand=True)
    results=queue.Queue();busy=False;fields=[];route=[]
    def render():
        for child in form.winfo_children():child.destroy()
        fields.clear();route.clear()
        if command.get() not in commands:
            ttk.Label(form,text="Use Assets → Voice containers for audio." if area.get()=="Audio" else "No available operation").pack(anchor="w")
            return
        def populate(p,host):
            for a in p._actions:
                if isinstance(a,argparse._HelpAction):continue
                if isinstance(a,argparse._SubParsersAction):
                    v=tk.StringVar(value=next(iter(a.choices)))
                    ttk.Label(host,text="Operation").pack(anchor="w")
                    ttk.Combobox(host,textvariable=v,values=list(a.choices),state="readonly").pack(fill="x")
                    child=ttk.Frame(host);child.pack(fill="x")
                    start=len(fields);depth=len(route);route.append(v)
                    def change(*_):
                        del fields[start:];del route[depth+1:]
                        for w in child.winfo_children():w.destroy()
                        populate(a.choices[v.get()],child)
                    v.trace_add("write",change);change()
                    continue
                row=ttk.Frame(host);row.pack(fill="x")
                ttk.Label(row,text=a.dest.replace("_"," ").title(),width=22).pack(side="left")
                flag=isinstance(a,(argparse._StoreTrueAction,argparse._StoreFalseAction))
                multi=a.nargs in ("+","*") or isinstance(a.nargs,int) or isinstance(a,argparse._AppendAction)
                default=a.default
                v=tk.BooleanVar(value=False) if flag else tk.StringVar(value="" if default is None or default==argparse.SUPPRESS else ("|".join(map(str,default)) if isinstance(default,(list,tuple)) else str(default)))
                if flag:ttk.Checkbutton(row,variable=v).pack(side="left")
                elif a.choices and not multi:ttk.Combobox(row,textvariable=v,values=list(a.choices),state="readonly").pack(side="left",fill="x",expand=True)
                else:
                    ttk.Entry(row,textvariable=v).pack(side="left",fill="x",expand=True)
                    if multi:ttk.Label(row,text="Separate values with |").pack(side="right")
                    else:
                        ttk.Button(row,text="File",command=lambda v=v:pick(v,filedialog.askopenfilename)).pack(side="right")
                        ttk.Button(row,text="Folder",command=lambda v=v:pick(v,filedialog.askdirectory)).pack(side="right")
                        ttk.Button(row,text="Save as",command=lambda v=v:pick(v,filedialog.asksaveasfilename)).pack(side="right")
                fields.append((a,v,flag,multi))
        populate(commands[command.get()],form)
    def pick(v,dialog):
        value=dialog()
        if value:v.set(value)
    def select(*_):
        values=GROUPS[area.get()];choices.configure(values=values);command.set(values[0] if values else "")
    command.trace_add("write",lambda *_:render());area.trace_add("write",select);select()
    def run():
        nonlocal busy
        if busy or not command.get():return
        argv=[command.get()]+[v.get() for v in route]
        try:
            for a,v,flag,multi in fields:
                value=v.get()
                if flag:
                    if value:argv.append(a.option_strings[0])
                    continue
                if not value:
                    if a.required:raise ValueError("Required: "+a.dest)
                    continue
                values=value.split("|") if multi else [value]
                if isinstance(a,argparse._AppendAction):
                    for x in values:argv.extend([a.option_strings[0],x])
                else:
                    if a.option_strings:argv.append(a.option_strings[0])
                    argv.extend(values)
            parser.parse_args(argv)
        except (ValueError,SystemExit) as exc:messagebox.showerror("Tool parameters","Check required fields and value types.");return
        if not messagebox.askyesno("Run tool","Run "+command.get()+" with the selected settings? This may write files or invoke installed tools."):return
        busy=True
        def worker():
            try:
                r=subprocess.run([sys.executable,"-m","chimster",*argv],capture_output=True,text=True,timeout=300)
                results.put(f"Exit {r.returncode}\n"+r.stdout+"\n"+r.stderr)
            except Exception as exc:results.put(str(exc))
        threading.Thread(target=worker,daemon=True).start()
    def poll():
        nonlocal busy
        try:
            value=results.get_nowait();busy=False;out.delete("1.0","end");out.insert("1.0",value)
        except queue.Empty:pass
        if parent.winfo_exists():parent.after(150,poll)
    ttk.Button(bar,text="Run",command=run).pack(side="left")
    poll()
