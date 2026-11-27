"""Desktop access to existing CLI commands; no shell evaluation."""
import sys, subprocess, threading, queue, json
import tkinter as tk
from tkinter import ttk, messagebox

GROUPS={
"Core":("dependencies","project","extension-info"),
"Compatibility":("compatibility","tes3-inventory"),
"Records":("fnv-index","record-compare","record-build","master-reorder"),
"Mod management":("loadorder","install-zip","fomod","stage-overlay","autopatch"),
"World":("fnv-world","building","chunk-build","chunk-load"),
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
    area=tk.StringVar(value="Records");command=tk.StringVar();args=tk.StringVar(value="[]")
    bar=ttk.Frame(parent);bar.pack(fill="x")
    group=ttk.Combobox(bar,textvariable=area,values=list(GROUPS),state="readonly");group.pack(side="left")
    choices=ttk.Combobox(bar,textvariable=command,state="readonly");choices.pack(side="left",fill="x",expand=True)
    ttk.Label(parent,text="Arguments as JSON array of strings. Help shows supported parameters.").pack(anchor="w")
    ttk.Entry(parent,textvariable=args).pack(fill="x")
    out=tk.Text(parent,wrap="word");out.pack(fill="both",expand=True)
    results=queue.Queue();busy=False
    def select(*_):
        values=GROUPS[area.get()];choices.configure(values=values);command.set(values[0] if values else "")
    area.trace_add("write",select);select()
    def run(help_only=False):
        nonlocal busy
        if busy:return
        try:
            cmd=command.get()
            if cmd not in GROUPS[area.get()]:raise ValueError("No available command")
            argv=["--help"] if help_only else json.loads(args.get())
            if not isinstance(argv,list) or not all(isinstance(x,str) for x in argv):raise ValueError("Expected JSON array of strings")
            if not help_only and not messagebox.askyesno("Run local tool",repr([cmd]+argv)+"\nMay write files or invoke installed tools. Continue?"):return
        except ValueError as exc:messagebox.showerror("Tool arguments",str(exc));return
        busy=True
        def worker():
            try:
                r=subprocess.run([sys.executable,"-m","chimster",cmd,*argv],capture_output=True,text=True,timeout=300)
                results.put(f"Exit {r.returncode}\n"+r.stdout+"\n"+r.stderr)
            except Exception as exc:results.put(str(exc))
        threading.Thread(target=worker,daemon=True).start()
    def poll():
        nonlocal busy
        try:
            value=results.get_nowait();busy=False;out.delete("1.0","end");out.insert("1.0",value)
        except queue.Empty:pass
        if parent.winfo_exists():parent.after(150,poll)
    ttk.Button(bar,text="Help",command=lambda:run(True)).pack(side="left")
    ttk.Button(bar,text="Run",command=run).pack(side="left")
    poll()
