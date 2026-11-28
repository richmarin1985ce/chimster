"""Desktop Cell View: worldspaces, cells, placements and a bounded grid."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from pprint import pformat
from .world_browser import Browser, label
from .native_profiles import canonical_profile


def mount(parent, game, open_preview=None):
    state = {"paths": [], "index": None, "world": None, "cell": None,
             "worlds": [], "cells": {}, "objects": {}, "center": (0, 0)}
    status = tk.StringVar(value="New Vegas only. Add plugins in master-first load order.")
    query = tk.StringVar()
    object_query = tk.StringVar()
    world_choice = tk.StringVar()
    radius = tk.StringVar(value="0")
    state["models"] = None
    state["draft"] = None
    def choose_models():
        folder = filedialog.askdirectory(title="Choose game Data directory with loose meshes")
        if folder:
            from .world_models import LooseModels
            state["models"] = LooseModels(folder)
            status.set("Loose NIF preview enabled: "+folder)
    gx, gy = tk.StringVar(value="0"), tk.StringVar(value="0")
    toolbar = ttk.Frame(parent)
    toolbar.pack(fill="x")
    plugins = tk.Listbox(parent, height=3, exportselection=False)
    plugins.pack(fill="x")
    def allow_reset():
        return not (state.get('draft') and state['draft'].operations) or messagebox.askyesno('Discard draft?','Changing the load order or rebuilding discards the in-memory draft. Export first if needed. Continue?',parent=parent)
    def add():
        if not allow_reset():return
        for p in filedialog.askopenfilenames(filetypes=[("New Vegas plugins", "*.esm *.esp")]):
            if p not in state["paths"]:
                state["paths"].append(p)
        update_paths()
    def update_paths():
        if state.get('draft') and state['draft'].operations:
            status.set('Export draft before changing load order; current draft discarded.')
        state["draft"] = None
        plugins.delete(0, "end")
        for p in state["paths"]:
            plugins.insert("end", Path(p).name)
        state["index"] = None
        worlds.configure(values=[])
        world_choice.set("")
        clear_cells()
        status.set("Load order changed; rebuild the index.")
    def move(delta):
        if not plugins.curselection():
            return
        i = plugins.curselection()[0]
        j = i + delta
        if 0 <= j < len(state["paths"]) and allow_reset():
            state["paths"][i], state["paths"][j] = state["paths"][j], state["paths"][i]
            update_paths()
            plugins.selection_set(j)
    def remove():
        if plugins.curselection() and allow_reset():
            state["paths"].pop(plugins.curselection()[0])
            update_paths()
    def load():
        if not allow_reset():return
        try:
            if canonical_profile(game.get()) != "new-vegas":
                raise ValueError("Select New Vegas in the main game selector.")
            if not state["paths"]:
                raise ValueError("Add plugins first.")
            index = Browser.open(state["paths"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            messagebox.showerror("Worldspace browser", str(exc))
            return
        state["index"] = index
        state["draft"] = None
        state["worlds"] = [None] + [r["key"] for r in index.matching(index.worlds.values(), "")]
        worlds.configure(values=["Interiors / unassigned"] +
                         [index.name(index.worlds[k]) + " [" + label(k) + "]" for k in state["worlds"][1:]])
        worlds.current(0)
        select_world()
        status.set(f"{len(index.worlds)} worldspaces; {sum(map(len,index.cells.values()))} cells; "
                   f"{len(index.issues)} hierarchy/coordinate warnings")
    for name, cmd in (("Add plugins", add), ("Up", lambda: move(-1)), ("Down", lambda: move(1)),
                      ("Remove", remove), ("Build index", load)):
        ttk.Button(toolbar, text=name, command=cmd).pack(side="left")
    ttk.Button(toolbar,text="Loose models",command=choose_models).pack(side="left")
    selectors = ttk.Frame(parent)
    selectors.pack(fill="x", pady=4)
    ttk.Label(selectors, text="World Space").pack(side="left")
    worlds = ttk.Combobox(selectors, textvariable=world_choice, state="readonly", width=45)
    worlds.pack(side="left", fill="x", expand=True)
    ttk.Label(selectors, text="Filter cells").pack(side="left")
    ttk.Entry(selectors, textvariable=query, width=18).pack(side="left")
    pane = ttk.Panedwindow(parent, orient="horizontal")
    pane.pack(fill="both", expand=True)
    left, right = ttk.Frame(pane), ttk.Frame(pane)
    pane.add(left, weight=1)
    pane.add(right, weight=2)
    def table(parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", selectmode="browse", height=8)
        for key, name, width in columns:
            tree.heading(key, text=name)
            tree.column(key, width=width, minwidth=45)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)
        return tree
    cells = table(left, (("name","Cell",150),("grid","X, Y",75),("count","Records",55),("provider","Winning file",100)))
    nav = ttk.Frame(left)
    nav.pack(fill="x")
    ttk.Label(nav, text="X").pack(side="left")
    ttk.Entry(nav, textvariable=gx, width=6).pack(side="left")
    ttk.Label(nav, text="Y").pack(side="left")
    ttk.Entry(nav, textvariable=gy, width=6).pack(side="left")
    def jump():
        try:
            state["center"] = (int(gx.get()), int(gy.get()))
        except ValueError:
            status.set("Enter integer cell coordinates.")
            return
        draw_grid()
        index = state["index"]
        if index is not None:
            candidates = index.coordinates.get((state["world"], state["center"]), ())
            if len(candidates) == 1:
                select_key(candidates[0]["key"])
            elif candidates:
                status.set("Multiple cells occupy these coordinates; select one in the list.")
    ttk.Button(nav, text="Go", command=jump).pack(side="left")
    ttk.Label(nav,text="Radius").pack(side="left")
    ttk.Combobox(nav,textvariable=radius,values=("0","1","2"),state="readonly",width=3).pack(side="left")
    canvas = tk.Canvas(left, height=200, background="#20252c", highlightthickness=0)
    canvas.pack(fill="x")
    ttk.Label(right, text="Cell objects / LAND / NAVM").pack(anchor="w")
    ttk.Entry(right, textvariable=object_query).pack(fill="x")
    objects = table(right, (("name","Object",150),("type","Type",55),("base","Base",110),("bucket","Bucket",80),("plugin","Winning file",100)))
    details = tk.Text(right, height=8, wrap="word", state="disabled")
    details.pack(fill="both", expand=True)
    ttk.Label(parent, textvariable=status).pack(anchor="w")
    def show(value):
        details.configure(state="normal")
        details.delete("1.0", "end")
        details.insert("1.0", pformat(value, width=80))
        details.configure(state="disabled")
    def clear_objects():
        objects.delete(*objects.get_children())
        state["objects"].clear()
    def clear_cells():
        cells.delete(*cells.get_children())
        state["cells"].clear()
        state["cell"] = None
        clear_objects()
        show({})
        draw_grid()
    def select_world(event=None):
        i = worlds.current()
        if state["index"] is None or i < 0:
            return
        state["world"] = state["worlds"][i]
        state["center"] = (0, 0)
        rows = state["index"].cell_rows(state["world"])
        grids = [r["grid"] for r in rows if "grid" in r]
        if grids:
            state["center"] = min(grids, key=lambda p: p[0]*p[0]+p[1]*p[1])
        gx.set(str(state["center"][0]))
        gy.set(str(state["center"][1]))
        refresh_cells()
    def refresh_cells(*_):
        clear_cells()
        index = state["index"]
        if index is None:
            return
        for row in index.cell_rows(state["world"], query.get()):
            key = row["key"]
            grid = row.get("grid")
            position = ", ".join(map(str,grid)) if grid is not None else ("Interior" if row.get("interior") else "Persistent / no grid")
            item = cells.insert("", "end", values=(index.name(row), position, len(index.children.get(key,())),row["plugin"]))
            state["cells"][item] = key
        draw_grid()
    def refresh_objects(*_):
        clear_objects()
        index = state["index"]
        if index is None or state["cell"] is None:
            return
        for row in index.object_rows(state["cell"], object_query.get()):
            base = index.active.get(row.get("base"))
            bucket = {8:"Persistent",9:"Temporary",10:"Distant"}.get(row["bucket"],"")
            item = objects.insert("", "end", values=(index.name(row),row["signature"],
                index.name(base) if base else label(row.get("base")),bucket,row["plugin"]))
            state["objects"][item] = row
    def select_key(key):
        for item, candidate in state["cells"].items():
            if candidate == key:
                cells.selection_set(item)
                cells.see(item)
                select_cell()
                return
        status.set("Cell is outside the current filter.")
    def select_cell(event=None):
        selected = cells.selection()
        index = state["index"]
        if not selected or index is None or selected[0] not in state["cells"]:
            return
        key = state["cells"][selected[0]]
        state["cell"] = key
        row = index.active[key]
        if "grid" in row:
            state["center"] = row["grid"]
            gx.set(str(row["grid"][0]))
            gy.set(str(row["grid"][1]))
        refresh_objects()
        show(index.details(row))
        draw_grid()
    def select_object(event=None):
        selected = objects.selection()
        if selected and selected[0] in state["objects"]:
            show(state["index"].details(state["objects"][selected[0]]))
    def draw_grid(event=None):
        canvas.delete("all")
        index = state["index"]
        if index is None or state["world"] is None:
            canvas.create_text(8,8,anchor="nw",fill="white",text="Select an exterior worldspace")
            return
        size = max(10,min(canvas.winfo_width(),canvas.winfo_height())//9)
        cx,cy = state["center"]
        for dy in range(-4,5):
            for dx in range(-4,5):
                grid = (cx+dx,cy-dy)
                rows = index.coordinates.get((state["world"],grid),())
                selected = any(r["key"]==state["cell"] for r in rows)
                color = "#d8ac63" if selected else "#b85c5c" if len(rows)>1 else "#52798a" if rows else "#303a43"
                x,y=(dx+4)*size,(dy+4)*size
                tag=f"cell_{dx+4}_{dy+4}"
                canvas.create_rectangle(x,y,x+size,y+size,fill=color,outline="#1d242a",tags=(tag,))
                if rows and len(rows)==1:
                    canvas.tag_bind(tag,"<Button-1>",lambda event,k=rows[0]["key"]:select_key(k))
                if size>=19:
                    canvas.create_text(x+size/2,y+size/2,text=f"{grid[0]}\n{grid[1]}",fill="white",font=("TkDefaultFont",7),tags=(tag,))
    def render_cell(focus=None):
        if canonical_profile(game.get())!='new-vegas':
            status.set('Select New Vegas to load this preview.');return
        if state['index'] is None or state['cell'] is None or open_preview is None:
            status.set('Select a cell first.');return
        try:
            from .world_preview import preview
            scene, report = preview(state['index'],state['cell'],int(radius.get()),state['models'])
            if open_preview(scene,report,focus,viewport_select):
                show(report)
        except (OSError,ValueError,TypeError,KeyError) as exc:
            messagebox.showerror('Cell preview',str(exc),parent=parent)
    def viewport_select(instance):
        index=state["index"]
        if not instance or index is None:return
        target=instance.removeprefix("land:")
        row=next((r for k,r in index.active.items() if label(k)==target),None)
        if row is None:return
        if row.get("cell")!=state["cell"]:
            owner=index.active.get(row.get("cell"))
            if owner and owner.get("world")==state["world"]:
                select_key(owner["key"])
        for item,ref in state["objects"].items():
            if ref["key"]==row["key"]:
                objects.selection_set(item);objects.see(item);break
        show(index.details(row))
    def render_object(event=None):
        selected=objects.selection()
        if selected and selected[0] in state['objects']:
            render_cell(label(state['objects'][selected[0]]['key']))
    ttk.Button(nav,text='Load 3D',command=render_cell).pack(side='left')
    cells.bind('<Double-1>',lambda e:render_cell())
    objects.bind('<Double-1>',render_object)
    def edit_draft(action):
        index=state["index"]
        if index is None:return
        from .world_draft import Draft
        draft=state["draft"]
        if draft is None:
            draft=Draft(index)
            state["draft"]=draft
        key=state["cell"]
        try:
            if action in ("new","rename"):
                value=simpledialog.askstring("Draft cell","Editor ID",parent=parent)
                if not value:return
                if action=="new":
                    grid=(int(gx.get()),int(gy.get())) if state["world"] is not None else None
                    key=draft.create(value,state["world"],grid)
                else:draft.rename(key,value)
            elif action=="place":
                if key is None:return
                base_name=simpledialog.askstring("Place static","Static editor ID (exact)",parent=parent)
                if not base_name:return
                found=[r for r in index.active.values() if r["signature"]=="STAT" and r["editor_id"].casefold()==base_name.casefold()]
                if len(found)!=1:raise ValueError("Static editor ID missing or ambiguous")
                default=index.active[key].get("grid")
                default=f"{default[0]*4096+2048},{default[1]*4096+2048},0" if default is not None else "0,0,0"
                coords=simpledialog.askstring("Place static","World X,Y,Z in game units",initialvalue=default,parent=parent)
                if coords is None:return
                draft.place(key,found[0]["key"],tuple(float(v) for v in coords.split(",")))
            elif action=="undo":draft.undo()
            elif action=="redo":draft.redo()
            elif action=="esp":
                from .world_draft_native import export_esp
                folder=filedialog.askdirectory(title="Choose staging directory (not live game Data)")
                if folder:show(export_esp(draft,Path(folder)/draft.name))
                return
            elif action=="export":
                p=filedialog.asksaveasfilename(defaultextension=".json",filetypes=[("Draft operations","*.json")])
                if p:draft.export(p)
                return
            state["index"]=draft.index()
            refresh_cells()
            if key is not None:select_key(key)
            status.set(f"Draft: {len(draft.operations)} staged operations; source plugins unchanged")
        except (OSError,ValueError,TypeError,KeyError) as exc:
            messagebox.showerror("World edit draft",str(exc),parent=parent)
    editbar=ttk.Frame(parent)
    editbar.pack(fill="x",before=pane)
    for title,action in (("New cell","new"),("Rename","rename"),("Place static","place"),("Undo","undo"),("Redo","redo"),("Export draft","export"),("Export ESP","esp")):
        ttk.Button(editbar,text=title,command=lambda a=action:edit_draft(a)).pack(side="left")
    def profile_changed(*_):
        # Preserve staged work; changing the game selector must not discard it.
        if state.get('draft') and state['draft'].operations:
            status.set('Existing New Vegas draft retained. Export before rebuilding for another profile.')
            return
        update_paths()
    worlds.bind("<<ComboboxSelected>>", select_world)
    cells.bind("<<TreeviewSelect>>", select_cell)
    objects.bind("<<TreeviewSelect>>", select_object)
    canvas.bind("<Configure>", draw_grid)
    query.trace_add("write",refresh_cells)
    object_query.trace_add("write",refresh_objects)
    game.trace_add("write",profile_changed)
    ttk.Button(toolbar,text="Warnings",command=lambda:show(state["index"].issues if state["index"] else [])).pack(side="left")
