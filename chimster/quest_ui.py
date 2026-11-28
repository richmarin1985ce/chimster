"""Desktop quest graph editor with JSON input, stage/choice preview and local flags."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import json
from .quest_editor import validate,Preview,load,save
EXAMPLE={"schema":1,"id":"ExampleQuest","start":"Start","nodes":[{"id":"Start","text":"A traveler requests help.","choices":[{"id":"Accept","text":"Agree","target":"End","sets":{"Accepted":True}},{"id":"Decline","text":"Decline","target":"End"}]},{"id":"End","text":"The encounter ends."}]}
def mount(parent):
    pane=ttk.Panedwindow(parent,orient="horizontal");pane.pack(fill="both",expand=True)
    editor=tk.Text(pane,wrap="none");pane.add(editor,weight=2);editor.insert("1.0",json.dumps(EXAMPLE,indent=2))
    side=ttk.Frame(pane);pane.add(side,weight=1)
    status=tk.StringVar();ttk.Label(side,textvariable=status,wraplength=300).pack(fill="x")
    choices=ttk.Frame(side);choices.pack(fill="both",expand=True);session=None
    def project():return json.loads(editor.get("1.0","end-1c"))
    def redraw():
        for w in choices.winfo_children():w.destroy()
        state=session.state();status.set(state["stage"]+"\n"+state["text"]+"\nFlags: "+str(state["flags"]))
        for e in state["choices"]:ttk.Button(choices,text=e["text"],command=lambda id=e["id"]:choose(id)).pack(fill="x")
        ttk.Button(choices,text="Undo choice",command=lambda:(session.undo(),redraw())).pack(fill="x")
    def choose(id):session.choose(id);redraw()
    def start():
        nonlocal session
        try:session=Preview(project());redraw()
        except (ValueError,KeyError,TypeError) as e:messagebox.showerror("Quest",str(e))
    def check():
        try:
            r=validate(project());status.set(json.dumps({k:v for k,v in r.items() if k!="localization"},indent=2))
        except (ValueError,KeyError,TypeError) as e:messagebox.showerror("Quest",str(e))
    def open_project(dropped=None):
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Quest JSON","*.json")])
        if p:
            try:editor.delete("1.0","end");editor.insert("1.0",json.dumps(load(p),indent=2))
            except (OSError,ValueError) as e:messagebox.showerror("Quest",str(e))
    def write():
        p=filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            try:save(project(),p)
            except (OSError,ValueError,KeyError,TypeError) as e:messagebox.showerror("Quest",str(e))
    def graph():
        from .quest_graph_ui import mount as graph_mount
        def set_project(p):editor.delete("1.0","end");editor.insert("1.0",json.dumps(p,indent=2))
        graph_mount(parent,project,set_project)
    def exact():
        from .quest_states import analyze
        try:status.set(json.dumps(analyze(project()),indent=2))
        except (ValueError,KeyError,TypeError) as e:messagebox.showerror("Quest",str(e))
    bar=ttk.Frame(parent);bar.pack(fill="x")
    for label,fn in (("Open",open_project),("Save as",write),("Validate",check),("Playtest",start),("Visual graph",graph),("Check states",exact)):ttk.Button(bar,text=label,command=fn).pack(side="left")
    from .drop_import import editor_drop
    editor_drop(parent,[([".json"],open_project,False)])
