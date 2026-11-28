"""Desktop Cell View: worldspaces, cells, placements and a bounded grid."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from pathlib import Path
from pprint import pformat
from .world_browser import Browser, label, BROWSE_PROFILES
from .native_profiles import canonical_profile


def mount(parent, game, open_preview=None, viewport_drop=None):
    state = {"paths": [], "index": None, "world": None, "cell": None,
             "worlds": [], "cells": {}, "objects": {}, "center": (0, 0)}
    status = tk.StringVar(value="Add plugins in master-first load order. Native editing: New Vegas.")
    query = tk.StringVar()
    object_query = tk.StringVar()
    world_choice = tk.StringVar()
    radius = tk.StringVar(value="0")
    state["models"] = None
    state["loose"] = None
    state["archives"] = ()
    state["draft"] = None
    def choose_models(dropped=None):
        folder = dropped if dropped is not None else filedialog.askdirectory(title="Choose game Data directory with loose meshes")
        if folder:
            from .world_models import LooseModels
            state["loose"] = LooseModels(folder)
            configure_models()
            status.set("Loose NIF preview enabled: "+folder)
    def configure_models():
        from .world_models import ArchiveModels
        state["models"]=ArchiveModels(state["archives"],state["loose"]) if state["archives"] else state["loose"]
    def choose_archives(dropped=None):
        paths=dropped if dropped is not None else filedialog.askopenfilenames(title="Select BSAs in low-to-high priority order",filetypes=[("Bethesda archives","*.bsa")])
        if not paths:return
        if not messagebox.askyesno("Archive preview order","Later archives win; loose files override. Confirm order:\\n"+"\\n".join(Path(p).name for p in paths),parent=parent):return
        try:
            from .world_models import ArchiveModels
            candidate=ArchiveModels(paths,state["loose"])
            state["archives"]=paths;state["models"]=candidate
            status.set(f"{len(paths)} archive layers indexed")
        except (OSError,ValueError) as exc:messagebox.showerror("Archive models",str(exc),parent=parent)
    gx, gy = tk.StringVar(value="0"), tk.StringVar(value="0")
    toolbar = ttk.Frame(parent)
    toolbar.pack(fill="x")
    plugins = tk.Listbox(parent, height=3, exportselection=False)
    plugins.pack(fill="x")
    def allow_reset():
        return not (state.get('draft') and state['draft'].operations) or messagebox.askyesno('Discard draft?','Changing the load order or rebuilding discards the in-memory draft. Export first if needed. Continue?',parent=parent)
    def add(dropped=None):
        if not allow_reset():return
        for p in (dropped if dropped is not None else filedialog.askopenfilenames(filetypes=[("Bethesda plugins", "*.esm *.esp")])):
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
            profile=canonical_profile(game.get())
            if profile not in BROWSE_PROFILES:
                raise ValueError("Select a supported full-slot Bethesda profile.")
            if not state["paths"]:
                raise ValueError("Add plugins first.")
            index = Browser.open(state["paths"],profile)
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
    ttk.Button(toolbar,text="BSA models",command=choose_archives).pack(side="left")
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
        if state['index'] is not None and canonical_profile(game.get())!=state['index'].profile:
            status.set('Select the loaded browser profile.');return
        if state['index'] is None or state['cell'] is None or open_preview is None:
            status.set('Select a cell first.');return
        try:
            from .world_preview import preview, Neighborhood
            scene, report = preview(state['index'],state['cell'],int(radius.get()),state['models'] if state['index'].profile=="new-vegas" else None)
            index=state['index']
            loader=Neighborhood(index,state['cell'],int(radius.get()),state['models'] if index.profile=='new-vegas' else None)
            def stream(x,y):
                if state['index'] is not index or canonical_profile(game.get())!=index.profile:return None
                result=loader.move(x,y)
                if result is not None:
                    select_key(loader.key)
                    show(result[1])
                return result
            if open_preview(scene,report,focus,viewport_select,stream):
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
    def edit_draft(action,drop=None):
        index=state["index"]
        if index is None and action=="new_world" and not state["paths"] and canonical_profile(game.get())=="new-vegas":
            index=Browser.open([])
            state["index"]=index
            state["world"]=None
        if index is None:return
        if index.profile!="new-vegas" or canonical_profile(game.get())!="new-vegas":
            status.set("Native world editing is currently New Vegas only.");return
        from .world_draft import Draft
        draft=state["draft"]
        if draft is None:
            draft=Draft(index)
            state["draft"]=draft
        key=state["cell"]
        try:
            if action=="new_world":
                name=simpledialog.askstring("New worldspace","Editor ID",parent=parent)
                if not name:return
                title=simpledialog.askstring("New worldspace","Display name",initialvalue=name,parent=parent)
                if title is None:return
                raw=simpledialog.askstring("New worldspace","Origin X,Y, width,height in cells (maximum 256 cells)",initialvalue="0,0,1,1",parent=parent)
                if raw is None:return
                x,y,w,h=map(int,raw.split(","))
                world=draft.create_world(name,title,(x,y),(w,h))
                state["world"]=world;key=None
            elif action=="weather":
                import json
                from .world_weather import defaults
                name=simpledialog.askstring("New weather","Editor ID",parent=parent)
                if not name:return
                win=tk.Toplevel(parent);win.title("New weather");win.transient(parent)
                ttk.Label(win,text="Edit the native weather specification. Colors are RGBA, six times per color type; DATA contains wind, cloud speeds, transition, sun, precipitation, lightning and classification bytes.",wraplength=650).pack(anchor="w")
                editor=tk.Text(win,width=80,height=22);editor.pack(fill="both",expand=True)
                editor.insert("1.0",json.dumps(defaults(),indent=2))
                def save_weather():
                    try:
                        if state["index"] is not index or state["draft"] is not draft:raise ValueError("Draft changed; reopen dialog")
                        draft.create_weather(name,json.loads(editor.get("1.0","end")))
                        state["index"]=draft.index();refresh_cells()
                        status.set("Weather staged; assign through a climate or region.")
                        win.destroy()
                    except (ValueError,TypeError,KeyError,OverflowError) as exc:messagebox.showerror("Weather",str(exc),parent=win)
                ttk.Button(win,text="Stage weather",command=save_weather).pack(pady=6)
                return
            elif action=="region":
                world=state["world"]
                if world is None:raise ValueError("Select an exterior worldspace")
                import json
                name=simpledialog.askstring("New region","Editor ID",parent=parent)
                if not name:return
                x,y=state["center"];x*=4096;y*=4096
                spec={"areas":[{"points":[[x,y],[x+4096,y],[x+4096,y+4096],[x,y+4096]],"falloff":0}],"weather":[],"music":None,"priority":0,"map_name":name}
                win=tk.Toplevel(parent);win.title("New region");win.transient(parent)
                ttk.Label(win,text="Polygon vertices in game units; weather entries: [[plugin, local ID], chance, global or null].").pack(anchor="w")
                editor=tk.Text(win,width=72,height=18);editor.pack(fill="both",expand=True)
                editor.insert("1.0",json.dumps(spec,indent=2))
                def save_region():
                    try:
                        if state["index"] is not index or state["draft"] is not draft:raise ValueError("Draft changed; reopen dialog")
                        values=json.loads(editor.get("1.0","end"));values["world"]=(world.origin,world.local)
                        draft.create_region(name,values)
                        state["index"]=draft.index();refresh_cells()
                        status.set("Region staged; export ESP to publish.")
                        win.destroy()
                    except (ValueError,TypeError,KeyError,OverflowError) as exc:messagebox.showerror("Region",str(exc),parent=win)
                ttk.Button(win,text="Stage region",command=save_region).pack(pady=6)
                return
            elif action=="climate":
                name=simpledialog.askstring("New climate","Editor ID",parent=parent)
                if not name:return
                weather=[r for r in index.active.values() if r["signature"]=="WTHR"]
                if not weather:raise ValueError("Load a plugin with weather records first")
                win=tk.Toplevel(parent);win.title("New climate");win.transient(parent)
                ttk.Label(win,text="Select weather records and assign chances totaling 100.").pack(anchor="w")
                tablebox=ttk.Frame(win);tablebox.pack(fill="both",expand=True)
                listing=tk.Listbox(tablebox,selectmode="extended",exportselection=False,height=12,width=55)
                listing.pack(side="left",fill="both",expand=True)
                scroll=ttk.Scrollbar(tablebox,command=listing.yview);scroll.pack(side="right",fill="y")
                listing.configure(yscrollcommand=scroll.set)
                weather.sort(key=lambda r:index.name(r).casefold())
                for row in weather:listing.insert("end",index.name(row)+" ["+label(row["key"])+"]")
                sun=tk.StringVar();glare=tk.StringVar()
                for title,var in (("Sun DDS texture",sun),("Sun glare DDS texture",glare)):
                    ttk.Label(win,text=title).pack(anchor="w");ttk.Entry(win,textvariable=var).pack(fill="x")
                timing=tk.StringVar(value="36,48,108,120,0,0")
                chances=tk.StringVar(value="100")
                ttk.Label(win,text="Chances in selection order").pack(anchor="w")
                ttk.Entry(win,textvariable=chances).pack(fill="x")
                ttk.Label(win,text="Sunrise begin/end, sunset begin/end, volatility, moon byte").pack(anchor="w")
                ttk.Entry(win,textvariable=timing).pack(fill="x")
                def save_climate():
                    try:
                        chosen=[weather[i]["key"] for i in listing.curselection()]
                        weights=[int(x.strip()) for x in chances.get().split(",")]
                        if len(weights)!=len(chosen):raise ValueError("Provide one chance for each selected weather")
                        if state["draft"] is not draft or state["index"] is not index:raise ValueError("Draft changed; reopen dialog")
                        draft.create_climate(name,{"weather":[((k.origin,k.local),w,None) for k,w in zip(chosen,weights)],"timing":tuple(map(int,timing.get().split(","))),"sun":sun.get(),"glare":glare.get()})
                        state["index"]=draft.index();refresh_cells()
                        status.set("Climate staged; assign it in World Environment.")
                        win.destroy()
                    except (ValueError,TypeError,KeyError) as exc:messagebox.showerror("Climate",str(exc),parent=win)
                ttk.Button(win,text="Create climate",command=save_climate).pack(pady=6)
                return
            elif action=="environment":
                world=state["world"]
                if world is None:return
                import json
                from .world_environment import FIELDS,LINKS,TEXTURES,effective
                row=index.worlds[world]
                win=tk.Toplevel(parent);win.title("Worldspace environment");win.transient(parent)
                ttk.Label(win,text="Heights in game units. Flags are a numeric bitmask. Links use plugin and local FormID.").pack(anchor="w",padx=8,pady=4)
                body=ttk.Frame(win,padding=8);body.pack(fill="both",expand=True)
                labels={"inheritance":"Parent inheritance flags (0–63)","heights":"Land, water heights","lod_height":"LOD water height","map_size_bounds":"Map size X,Y; NW X,Y; SE X,Y","map_offset":"Map scale, X,Y offsets","flags":"World flags (byte)"}
                fields={}
                env=row.get("environment",{})
                for i,name in enumerate(FIELDS):
                    ttk.Label(body,text=labels[name]).grid(row=i,column=0,sticky="w",pady=3)
                    value=tk.StringVar(value=",".join(map(str,env[name])) if name in env else "")
                    ttk.Entry(body,textvariable=value,width=35).grid(row=i,column=1,sticky="ew",pady=3)
                    fields[name]=value
                textures={}
                for i,name in enumerate(TEXTURES,len(FIELDS)):
                    ttk.Label(body,text=name.replace("_"," ").title()).grid(row=i,column=0,sticky="w",pady=3)
                    var=tk.StringVar(value=env.get(name,""));textures[name]=var
                    ttk.Entry(body,textvariable=var,width=35).grid(row=i,column=1,sticky="ew")
                choices={}
                for i,(name,(_,sig)) in enumerate(LINKS.items(),len(FIELDS)+len(TEXTURES)):
                    items=[r for r in index.active.values() if r["signature"]==sig and r["key"]!=world]
                    items.sort(key=lambda r:index.name(r).casefold())
                    options={"(unchanged)":None,"(clear)":None}
                    for item in items:
                        k=item["key"];options[index.name(item)+" ["+label(k)+"]"]=(k.origin,k.local)
                    value=tk.StringVar(value=next((s for s,k in options.items() if k is not None and k==env.get(name)),"(unchanged)"))
                    ttk.Label(body,text=name.replace("_"," ").title()).grid(row=i,column=0,sticky="w",pady=3)
                    ttk.Combobox(body,values=list(options),textvariable=value,state="readonly",width=35).grid(row=i,column=1,sticky="ew")
                    choices[name]=(value,options)
                ttk.Label(win,text="Blank numeric fields unchanged. 0x02: no fast travel; 0x10: no LOD water. Land height does not reshape existing LAND.").pack(anchor="w",padx=8)
                def save():
                    try:
                        changes={}
                        for name,var in fields.items():
                            raw=var.get().strip()
                            if not raw:continue
                            parts=raw.split(",")
                            value=tuple(int(v,0) for v in parts) if name in ("flags","inheritance","map_size_bounds") else tuple(float(v) for v in parts)
                            if value!=env.get(name):changes[name]=value
                        for name,var in textures.items():
                            value=var.get().strip() or None
                            if value!=env.get(name):changes[name]=value
                        for name,(var,options) in choices.items():
                            choice=var.get()
                            if choice!="(unchanged)" and options[choice]!=env.get(name):changes[name]=options[choice]
                        if changes:
                            if state["draft"] is not draft or state["index"] is not index:raise ValueError("Draft changed; reopen properties")
                            draft.set_environment(world,changes)
                            state["index"]=draft.index();refresh_cells()
                            show(state["index"].details(state["index"].worlds[world]))
                            status.set("World environment staged; export ESP to publish")
                        win.destroy()
                    except (ValueError,TypeError,KeyError,OSError) as exc:messagebox.showerror("Environment",str(exc),parent=win)
                ttk.Label(win,text="Parent bits: land 1, LOD 2, map 4, water 8, climate 16, image space 32.").pack(anchor="w",padx=8)
                controls=ttk.Frame(win);controls.pack(fill="x",pady=8)
                ttk.Button(controls,text="Stage changes",command=save).pack(side="left")
                ttk.Button(controls,text="Effective settings",command=lambda:show(effective(index,world))).pack(side="left")
                return
            elif action=="world":
                world=state["world"]
                if world is None:return
                row=index.worlds[world]
                name=simpledialog.askstring("Worldspace properties","Editor ID",initialvalue=row["editor_id"],parent=parent)
                if not name:return
                title=simpledialog.askstring("Worldspace properties","Display name",initialvalue=row["name"],parent=parent)
                if title is None:return
                draft.world_properties(world,name,title)
            elif action=="duplicate":
                if key is None:return
                row=index.active[key]
                name=simpledialog.askstring("Duplicate cell","New editor ID",parent=parent)
                if not name:return
                grid=None
                if row.get("world") is not None:
                    value=simpledialog.askstring("Duplicate cell","Destination X,Y",initialvalue=f"{row['grid'][0]+1},{row['grid'][1]}",parent=parent)
                    if not value:return
                    grid=tuple(map(int,value.split(",")))
                if not messagebox.askyesno("Duplicate static cell","Copies the cell shell and eligible static objects only. LAND, navigation, persistent objects, links and cell settings are not copied. Continue?",parent=parent):return
                key,report=draft.duplicate(key,name,grid,static_only=True)
            elif action in ("new","rename"):
                value=simpledialog.askstring("Draft cell","Editor ID",parent=parent)
                if not value:return
                if action=="new":
                    grid=(int(gx.get()),int(gy.get())) if state["world"] is not None else None
                    key=draft.create(value,state["world"],grid)
                else:draft.rename(key,value)
            elif action=="drop":
                key,base,position=drop
                draft.place(key,base,position)
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
            elif action=="transform":
                selected=objects.selection()
                if not selected or selected[0] not in state["objects"]:return
                ref=state["objects"][selected[0]]
                from math import degrees,radians
                if ref["signature"]!="REFR" or "position" not in ref:
                    raise ValueError("Select a temporary static reference")
                current=(*ref["position"],degrees(ref["rotation"][2]),ref.get("scale",1))
                values=simpledialog.askstring("Transform reference","X,Y,Z, yaw degrees, scale",initialvalue=",".join(map(str,current)),parent=parent)
                if values is None:return
                x,y,z,yaw,scale=map(float,values.split(","))
                draft.transform(ref["key"],(x,y,z),radians(yaw),scale)
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
            updated=state["index"]
            current_world=state["world"]
            state["worlds"]=[None]+[r["key"] for r in updated.matching(updated.worlds.values(),"")]
            worlds.configure(values=["Interiors / unassigned"]+[updated.name(updated.worlds[k])+" ["+label(k)+"]" for k in state["worlds"][1:]])
            worlds.current(state["worlds"].index(current_world) if current_world in state["worlds"] else 0)
            state["world"]=state["worlds"][worlds.current()]
            refresh_cells()
            if key is not None:select_key(key)
            status.set(f"Draft: {len(draft.operations)} staged operations; source plugins unchanged")
            if action=="duplicate":show(report)
        except (OSError,ValueError,TypeError,KeyError) as exc:
            messagebox.showerror("World edit draft",str(exc),parent=parent)
    editbar=ttk.Frame(parent)
    editbar.pack(fill="x",before=pane)
    for title,action in (("New world","new_world"),("World properties","world"),("Environment","environment"),("New climate","climate"),("New weather","weather"),("New region","region"),("New cell","new"),("Rename","rename"),("Duplicate","duplicate"),("Place static","place"),("Transform","transform"),("Undo","undo"),("Redo","redo"),("Export draft","export"),("Export ESP","esp")):
        ttk.Button(editbar,text=title,command=lambda a=action:edit_draft(a)).pack(side="left")
    def object_palette():
        if state["index"] is None:return
        if state["index"].profile!="new-vegas":
            status.set("Static placement is New Vegas only.");return
        win=tk.Toplevel(parent);win.title("Static Object Window");win.geometry("410x440")
        search=tk.StringVar()
        ttk.Label(win,text="Drag a static onto a cell, grid or open native viewport.").pack(anchor="w")
        ttk.Entry(win,textvariable=search).pack(fill="x")
        listing=table(win,(("name","Editor ID",180),("file","Plugin",120)))
        rows={}
        drag={"key":None,"start":None}
        def populate(*_):
            listing.delete(*listing.get_children());rows.clear()
            index=state["index"]
            if index is None:return
            items=index.matching((r for r in index.active.values() if r["signature"]=="STAT"),search.get())
            for row in items[:2000]:
                item=listing.insert("","end",values=(index.name(row),row["plugin"]))
                rows[item]=row["key"]
        def begin(e):
            drag["key"]=rows.get(listing.identify_row(e.y))
            drag["start"]=(e.x_root,e.y_root)
        def release(e):
            base=drag["key"];start=drag["start"]
            drag["key"]=None;drag["start"]=None
            if base is None or start is None or abs(e.x_root-start[0])+abs(e.y_root-start[1])<8:return
            index=state["index"]
            if index is None or base not in index.active:return
            def inside(widget):
                return widget.winfo_viewable() and widget.winfo_rootx()<=e.x_root<widget.winfo_rootx()+widget.winfo_width() and widget.winfo_rooty()<=e.y_root<widget.winfo_rooty()+widget.winfo_height()
            key=None;xy=None;z=0
            view_drop=viewport_drop(e.x_root,e.y_root) if viewport_drop else None
            if view_drop is not None:
                from math import floor
                token,pos=view_drop
                owner=next((r for k,r in index.active.items() if label(k)==token and r["signature"]=="CELL"),None)
                if owner is None or owner.get("world")!=state["world"]:return
                if owner.get("grid") is not None:
                    candidates=index.coordinates.get((owner["world"],tuple(floor(v/4096) for v in pos[:2])),())
                    if len(candidates)!=1:return
                    key=candidates[0]["key"]
                else:key=owner["key"]
                xy=pos[:2];z=pos[2]
            elif inside(canvas) and state["world"] is not None:
                size=max(10,min(canvas.winfo_width(),canvas.winfo_height())//9)
                px=e.x_root-canvas.winfo_rootx();py=e.y_root-canvas.winfo_rooty()
                if not 0<=px<9*size or not 0<=py<9*size:return
                col,row=px//size,py//size
                coord=(state["center"][0]+col-4,state["center"][1]+4-row)
                candidates=index.coordinates.get((state["world"],coord),())
                if len(candidates)!=1:
                    status.set("Drop requires one existing unambiguous cell.");return
                key=candidates[0]["key"]
                xy=(coord[0]*4096+(px%size)/size*4096,coord[1]*4096+(1-(py%size+.5)/size)*4096)
            elif inside(cells):
                key=state["cells"].get(cells.identify_row(e.y_root-cells.winfo_rooty()))
            if key is None:return
            row=index.active[key]
            if xy is None:
                grid=row.get("grid")
                xy=(grid[0]*4096+2048,grid[1]*4096+2048) if grid else (0,0)
            coords=simpledialog.askstring("Confirm static placement","World X,Y,Z (game units)",initialvalue=f"{xy[0]:.3f},{xy[1]:.3f},{z:.3f}",parent=parent)
            if coords is None:return
            try:position=tuple(map(float,coords.split(",")))
            except ValueError:messagebox.showerror("Placement","Expected three coordinates",parent=parent);return
            edit_draft("drop",(key,base,position))
            if view_drop is not None and state.get("cell")==key:
                render_cell()
        listing.bind("<ButtonPress-1>",begin,add="+")
        listing.bind("<ButtonRelease-1>",release,add="+")
        search.trace_add("write",populate)
        populate()
    ttk.Button(editbar,text="Object Window",command=object_palette).pack(side="left")
    def export_world_lod():
        index=state["index"];world=state["world"]
        if index is None or world is None:return
        folder=filedialog.askdirectory(title="Choose parent directory for portable LOD package")
        if not folder:return
        try:
            from .world_lod import export
            out=Path(folder)/("lod_"+world.origin.replace(".","_")+"_"+format(world.local,"06x"))
            show(export(index,world,out))
            status.set("Portable multi-resolution terrain LOD exported; not engine-native tiles.")
        except (ValueError,OSError,TypeError,KeyError) as exc:messagebox.showerror("World LOD",str(exc),parent=parent)
    ttk.Button(nav,text="Generate LOD",command=export_world_lod).pack(side="left")
    def native_lod():
        index=state["index"];world=state["world"]
        if index is None or world is None:return
        from .world_lod_native import prepare,launch,audit,world_name
        from .xedit import Workspace
        profile=filedialog.askopenfilename(title="Select staged LOD workspace JSON",filetypes=[("Workspace JSON","*.json")])
        if not profile:return
        executable=filedialog.askopenfilename(title="Select trusted xLODGen executable")
        if not executable:return
        try:
            workspace=Workspace.load(profile)
            plan=prepare(index,world,workspace,executable)
            show(plan)
            if plan["settings_missing"]:
                messagebox.showwarning("LODSettings missing","Create the matching LODSettings in a disposable game workspace, then retry.",parent=parent)
                return
            if not messagebox.askyesno("Native LOD","Launch xLODGen against the staged load order? Select "+plan["world"]+" in the external tool. Output is separate from Data.",parent=parent):return
            proc,plan=launch(index,world,workspace,executable)
            status.set("xLODGen running; finish generation in the external tool.")
            def poll():
                code=proc.poll()
                if code is None:
                    parent.after(1000,poll);return
                if code:
                    status.set("xLODGen exited with code "+str(code));return
                try:
                    report=audit(plan["output"],plan["world"],plan["game"]);show(report)
                    status.set("Native output audited; review before installation.")
                except (OSError,ValueError) as exc:status.set("LOD output: "+str(exc))
            parent.after(1000,poll)
        except (OSError,ValueError,KeyError,TypeError) as exc:messagebox.showerror("Native LOD",str(exc),parent=parent)
    ttk.Button(nav,text="Native LOD",command=native_lod).pack(side="left")
    def audit_lod():
        index=state["index"];world=state["world"]
        if index is None or world is None:return
        folder=filedialog.askdirectory(title="Choose generated native LOD output")
        if not folder:return
        try:
            from .world_lod_native import audit,world_name,GAME
            show(audit(folder,world_name(index,world),GAME.get(index.profile,index.profile)))
        except (ValueError,OSError) as exc:messagebox.showerror("Audit LOD",str(exc),parent=parent)
    ttk.Button(nav,text="Audit LOD",command=audit_lod).pack(side="left")
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
    from .drop_import import editor_drop
    editor_drop(parent,[((".esp",".esm"),add,True),((".bsa",),choose_archives,True),(("<directory>",),choose_models,False)],confirm=False,target=plugins)
