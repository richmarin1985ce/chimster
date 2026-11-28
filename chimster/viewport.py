"""Tk desktop viewport with an original portable scene model."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from dataclasses import replace
from pathlib import Path
from .scene import Scene,Instance,Camera,frame,demo_scene,load_obj

def mount(parent):
    from .gpu_viewport import Renderer, Settings, make_demo, load_materials
    from .render_effects import preset,LocalLight,FogVolume
    scene,materials=make_demo();camera=Camera();selected=None;drag=None
    effect_name=tk.StringVar(value="Off");water_enabled=tk.BooleanVar(value=False)
    point_enabled=tk.BooleanVar(value=False);spot_enabled=tk.BooleanVar(value=False)
    water_height=tk.StringVar(value="0");light_pos=tk.StringVar(value="2,2,5")
    custom_fx={};local_fx={};extra_volumes=()
    renderer=None;panda=None;photo=None;render_size=(1,1);settings=Settings();failure=''
    backend=tk.StringVar(value='Panda3D');lod_text=tk.StringVar(value='22,45,90')
    toolbar=ttk.Frame(parent);toolbar.pack(fill="x")
    pane=ttk.Panedwindow(parent,orient="horizontal");pane.pack(fill="both",expand=True)
    canvas=tk.Canvas(pane,bg="#1b232c",highlightthickness=0);pane.add(canvas,weight=4)
    side=ttk.Frame(pane,padding=6);pane.add(side,weight=1)
    objects=tk.Listbox(side,exportselection=False,height=9);objects.pack(fill="both",expand=True)
    values={k:tk.StringVar(value="0") for k in ("x","y","z","yaw","scale")}
    for k,v in values.items():
        row=ttk.Frame(side);row.pack(fill="x")
        ttk.Label(row,text=k,width=7).pack(side="left");ttk.Entry(row,textvariable=v,width=10).pack(side="right")
    status=tk.StringVar();ttk.Label(parent,textvariable=status).pack(fill="x")
    source=tk.StringVar(value="Portable scene");ttk.Label(parent,textvariable=source).pack(fill="x")
    native_preview=False
    selection_callback=None
    stream_callback=None;preview_origin=(0,0,0);pan_drag=None;preview_cell=None
    native_weather={}
    native_day=tk.StringVar(value="Day")
    def draw():
        nonlocal renderer,panda,photo,render_size,failure
        canvas.delete("mesh");canvas.delete("gl")
        try:
            pos=tuple(float(x) for x in light_pos.get().split(","))
            lights=(LocalLight(position=pos,direction=local_fx.get("direction",(0,0,-1)) if spot_enabled.get() else None,shadows=spot_enabled.get(),**{k:v for k,v in local_fx.items() if k!="direction"}),) if point_enabled.get() else ()
            effects=replace(preset(effect_name.get()),water_level=float(water_height.get()) if water_enabled.get() else None,lights=lights,fog_volumes=extra_volumes,**{**weather_effects(),**custom_fx}).validate()
        except ValueError as exc:
            status.set("Effects: "+str(exc));return
        if backend.get()=="Panda3D" and canvas.winfo_width()>4 and canvas.winfo_height()>4:
            try:
                from .panda_viewport import Preview
                from PIL import Image,ImageTk
                if panda is None:panda=Preview()
                w,h=canvas.winfo_width(),canvas.winfo_height()
                factor=min(1,1280/w,720/h);rw,rh=max(1,int(w*factor)),max(1,int(h*factor))
                raw=panda.render(scene,replace(camera,zoom=camera.zoom*factor),rw,rh,materials,settings,effects)
                photo=ImageTk.PhotoImage(Image.frombytes("RGBA",(rw,rh),raw).resize((w,h)))
                canvas.create_image(0,0,image=photo,anchor="nw",tags=("gl",))
                status.set("Panda3D | shadows / fog / water | AO: ModernGL only"+(" | reflection fallback: "+panda.water_error if panda.water_error else ""))
                return
            except Exception as e:
                failure="Panda3D: "+str(e)[:150];backend.set("ModernGL")
                if panda is not None:
                    try:panda.close()
                    except Exception:pass
                    panda=None
        if backend.get()=="ModernGL" and canvas.winfo_width()>4 and canvas.winfo_height()>4:
            try:
                from PIL import Image,ImageTk
                if renderer is None:renderer=Renderer()
                w,h=canvas.winfo_width(),canvas.winfo_height()
                factor=min(1,1280/w,720/h);rw,rh=max(1,int(w*factor)),max(1,int(h*factor))
                # Keep camera magnification consistent with the canvas.
                scaled=replace(camera,zoom=camera.zoom*factor)
                raw,stats=renderer.render(scene,scaled,rw,rh,materials,settings,selected,effects)
                image=Image.frombytes("RGBA",(rw,rh),raw)
                if (rw,rh)!=(w,h):image=image.resize((w,h),Image.Resampling.BILINEAR)
                photo=ImageTk.PhotoImage(image);render_size=(rw,rh)
                canvas.create_image(0,0,image=photo,anchor="nw",tags=("gl",))
                status.set(f'{stats["renderer"]} | {stats["triangles"]} tris | {stats["draw_calls"]} draws | {stats["culled"]} culled | {stats["frame_ms"]:.1f} ms | LOD {stats["lod_counts"]}' + (" | "+failure if failure else ""))
                return
            except Exception as e:
                failure=(failure+" | " if failure else "")+"ModernGL: "+str(e)[:150];backend.set("CPU")
                if renderer is not None:
                    try:renderer.close()
                    except Exception:pass
                    renderer=None
        canvas.delete("gl")
        rows=frame(scene,camera,max(1,canvas.winfo_width()),max(1,canvas.winfo_height()))
        for _,id,coords,color in rows:
            canvas.create_polygon(*coords,fill=color,outline="#d5c28f" if id==selected else "",tags=("mesh","obj:"+id))
        status.set(f"{len(scene.instances)} objects | {len(rows)} CPU preview triangles | right-drag orbit, wheel zoom"+(" | Renderer unavailable: "+failure if failure else ""))
    def sync():
        objects.delete(0,"end")
        for i,item in enumerate(scene.instances):
            objects.insert("end",item.id)
            if item.id==selected:objects.selection_set(i)
        item=next((i for i in scene.instances if i.id==selected),None)
        if item:
            for k,v in values.items():v.set(str(getattr(item,k)))
        else:
            for k,v in values.items():v.set("")
        draw()
    def select(event=None):
        nonlocal selected
        ids=objects.curselection()
        if ids:
            selected=scene.instances[ids[0]].id;sync()
            if native_preview and selection_callback:selection_callback(selected)
    def pick(e):
        nonlocal selected
        if backend.get()=="ModernGL" and renderer is not None:
            rw,rh=render_size
            selected=renderer.pick(int(e.x*rw/max(1,canvas.winfo_width())),int(e.y*rh/max(1,canvas.winfo_height())))
            sync()
            if native_preview and selection_callback:selection_callback(selected)
            return
        for item in reversed(canvas.find_overlapping(e.x-1,e.y-1,e.x+1,e.y+1)):
            tags=canvas.gettags(item)
            tag=next((t for t in tags if t.startswith("obj:")),None)
            if tag:
                selected=tag[4:];sync()
                if native_preview and selection_callback:selection_callback(selected)
                return
    def apply():
        if native_preview or not selected:return
        try:scene.update(selected,**{k:float(v.get()) for k,v in values.items()});sync()
        except ValueError as e:messagebox.showerror("Transform",str(e))
    def add():
        nonlocal selected
        if native_preview:return
        n=1
        while any(i.id==f"tree-new-{n}" for i in scene.instances):n+=1
        if "tree" not in scene.assets:return
        selected=f"tree-new-{n}";scene.add(Instance(selected,"tree"));sync()
    def delete():
        nonlocal selected
        if native_preview:return
        if selected and any(i.id==selected for i in scene.instances):
            scene.remove(selected);selected=None;sync()
    def open_scene(dropped=None):
        nonlocal scene,selected,native_preview
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Chimster scene","*.json")])
        if p:
            try:scene=Scene.load(p);selected=None;native_preview=False;source.set("Portable scene");sync()
            except (OSError,ValueError,KeyError,TypeError) as e:messagebox.showerror("Scene",str(e))
    def save_scene():
        if native_preview:return
        p=filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            try:scene.save(p)
            except (OSError,ValueError) as e:messagebox.showerror("Scene",str(e))
    def import_mesh(dropped=None):
        nonlocal selected
        if native_preview:return
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Triangulated OBJ","*.obj")])
        if p:
            try:
                m=load_obj(p);n=1
                while f"import-{n}" in scene.assets:n+=1
                key=f"import-{n}";scene.assets[key]=m;scene.add(Instance(key,key));selected=key;sync()
            except (OSError,ValueError) as e:messagebox.showerror("Mesh",str(e))
    def start(e):
        nonlocal drag
        drag=(e.x,e.y)
    def orbit(e):
        nonlocal drag,camera
        if drag:
            dx,dy=e.x-drag[0],e.y-drag[1];drag=(e.x,e.y)
            camera=replace(camera,yaw=camera.yaw+dx*.5,pitch=max(-85,min(85,camera.pitch+dy*.5)));draw()
    def pan_start(e):
        nonlocal pan_drag
        pan_drag=(e.x,e.y)
    def pan_move(e):
        nonlocal pan_drag,camera
        if pan_drag is None:return
        from math import radians,cos,sin
        dx,dy=e.x-pan_drag[0],e.y-pan_drag[1]
        pan_drag=(e.x,e.y)
        a=radians(camera.yaw);b=radians(camera.pitch)
        right=-dx/camera.zoom
        forward=-dy/(camera.zoom*max(.15,abs(sin(b))))
        x,y,z=camera.center
        camera=replace(camera,center=(x+cos(a)*right+sin(a)*forward,y-sin(a)*right+cos(a)*forward,z))
        draw()
    def weather_effects():
        sample=native_weather.get(native_day.get().lower()) if native_preview else None
        if not sample:return {}
        far=sample["far"]/128
        density=min(1,2.3/far) if far>0 else 0
        return {"fog_color":sample["fog_color"],"fog_density":density,"sun_color":sample["sun_color"],"ambient":sum(sample["ambient_color"])/3}
    def apply_world_environment(report):
        nonlocal native_weather
        native_weather=report.get("environment",{}).get("weather_preview") or {}
        # Native water level is a geometry height, not a material/engine simulation.
        env=report.get("environment",{}).get("values",{})
        heights=env.get("heights")
        if report.get("grid") is not None and heights is not None:
            water_height.set(str(heights[1]/128))
            water_enabled.set("water" in env)
        else:water_enabled.set(False)
    def pan_end(e):
        nonlocal pan_drag,camera,scene,materials,selected,preview_origin,preview_cell
        pan_drag=None
        if not native_preview or stream_callback is None:return
        absolute=tuple(camera.center[i]*128+preview_origin[i] for i in range(3))
        try:result=stream_callback(absolute[0],absolute[1])
        except (OSError,ValueError,TypeError,KeyError) as exc:
            status.set("Cell streaming: "+str(exc));return
        if result is None:return
        candidate,report=result
        scene=candidate;materials={};preview_origin=report["origin_game_units"];preview_cell=report["cell"]
        camera=replace(camera,center=tuple((absolute[i]-preview_origin[i])/128 for i in range(3)))
        apply_world_environment(report)
        if not any(i.id==selected for i in scene.instances):selected=None
        source.set(f"Read-only cell {report['cell']} | {report['cells']} cells | {report['land_tiles']} LAND tiles | {report.get('model_references',0)} models")
        sync()
    def zoom(delta):
        nonlocal camera
        camera=replace(camera,zoom=max(.05,min(2000,camera.zoom*(1.15 if delta>0 else 1/1.15))));draw()
    def fit():
        nonlocal camera
        from .scene import transformed
        pts=[p for i in scene.instances for p in transformed(scene.assets[i.asset],i)]
        if not pts:return
        lo=[min(p[k] for p in pts) for k in range(3)];hi=[max(p[k] for p in pts) for k in range(3)]
        size=max(1,max(hi[k]-lo[k] for k in range(3)))
        camera=replace(camera,center=tuple((a+b)/2 for a,b in zip(lo,hi)),zoom=max(.05,min(2000,min(canvas.winfo_width(),canvas.winfo_height())*.65/size)));draw()
    def set_lod():
        nonlocal settings
        try:
            thresholds=tuple(float(x.strip()) for x in lod_text.get().split(","))
            settings=replace(settings,lod_distances=thresholds).validate();draw()
        except ValueError as e:messagebox.showerror("LOD settings",str(e))
    def import_materials(dropped=None):
        nonlocal materials
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Material manifest","*.json")])
        if p:
            try:materials=load_materials(p);draw()
            except (OSError,ValueError,TypeError,ImportError) as e:messagebox.showerror("Materials",str(e))
    def release(e):
        nonlocal renderer,panda
        if e.widget is parent and panda is not None:
            try:panda.close()
            finally:panda=None
        if e.widget is parent and renderer is not None:
            try:renderer.close()
            finally:renderer=None
    parent.bind("<Destroy>",release,add="+")
    controls=ttk.Frame(parent);controls.pack(fill="x",before=pane)
    choice=ttk.Combobox(controls,textvariable=backend,values=("Panda3D","ModernGL","CPU"),state="readonly",width=12)
    choice.pack(side="left")
    def switch_backend(event=None):
        nonlocal renderer,panda,failure
        failure=""
        if backend.get()!="Panda3D" and panda is not None:
            try:panda.close()
            finally:panda=None
        if backend.get()!="ModernGL" and renderer is not None:
            try:renderer.close()
            finally:renderer=None
        draw()
    choice.bind("<<ComboboxSelected>>",switch_backend)
    def toggle_setting(name,value):
        nonlocal settings
        settings=replace(settings,**{name:value}).validate();draw()
    for name,label in (("cull","GL culling"),("instancing","GL instancing"),("hierarchy","GL hierarchy")):
        var=tk.BooleanVar(value=getattr(settings,name))
        ttk.Checkbutton(controls,text=label,variable=var,
            command=lambda n=name,v=var:toggle_setting(n,v.get())).pack(side="left")
    ttk.Label(controls,text="LOD distances").pack(side="left")
    ttk.Entry(controls,textvariable=lod_text,width=15).pack(side="left")
    ttk.Button(controls,text="Apply LOD",command=set_lod).pack(side="left")
    ttk.Button(controls,text="Load materials",command=import_materials).pack(side="left")
    fxbar=ttk.Frame(parent);fxbar.pack(fill="x",before=pane)
    ttk.Label(fxbar,text="Effects").pack(side="left")
    fxchoice=ttk.Combobox(fxbar,textvariable=effect_name,values=("Off","Low","Medium","High"),state="readonly",width=9)
    fxchoice.pack(side="left");fxchoice.bind("<<ComboboxSelected>>",lambda e:draw())
    ttk.Checkbutton(fxbar,text="Preview water (Panda)",variable=water_enabled,command=draw).pack(side="left")
    ttk.Checkbutton(fxbar,text="Local light",variable=point_enabled,command=draw).pack(side="left")
    ttk.Label(fxbar,text="Water Z").pack(side="left")
    ttk.Entry(fxbar,textvariable=water_height,width=6).pack(side="left")
    ttk.Checkbutton(fxbar,text="Spot",variable=spot_enabled,command=draw).pack(side="left")
    ttk.Label(fxbar,text="Light XYZ").pack(side="left")
    ttk.Entry(fxbar,textvariable=light_pos,width=12).pack(side="left")
    ttk.Button(fxbar,text="Apply",command=draw).pack(side="left")
    day_choice=ttk.Combobox(fxbar,textvariable=native_day,values=("Day","Night"),state="readonly",width=6)
    day_choice.pack(side="left");day_choice.bind("<<ComboboxSelected>>",lambda e:draw())
    def advanced_lighting():
        nonlocal custom_fx,local_fx,extra_volumes,settings
        import json
        win=tk.Toplevel(parent);win.title("Lighting and atmospheric controls")
        ttk.Label(win,text="ModernGL: nested shadow maps and volumetric lighting. Panda: native lights, shadows, distance fog.").pack(padx=8,pady=6)
        base=preset(effect_name.get())
        keys=("ambient","sun_intensity","sun_color","shadow_size","shadow_extent","shadow_cascades","shadow_bias","fog_density","fog_color","fog_height","fog_falloff","scatter_strength","scatter_anisotropy","volume_steps","volume_distance")
        fields={k:tk.StringVar(value=json.dumps(custom_fx.get(k,getattr(base,k)))) for k in keys}
        fields["sun_direction"]=tk.StringVar(value=json.dumps(settings.light))
        light=LocalLight()
        for k in ("color","intensity","radius","cone","direction"):
            fields["local_"+k]=tk.StringVar(value=json.dumps(local_fx.get(k,getattr(light,k) if k!="direction" else (0,0,-1))))
        from dataclasses import asdict
        fields["fog_volumes"]=tk.StringVar(value=json.dumps([asdict(v) for v in extra_volumes]))
        body=ttk.Frame(win,padding=8);body.pack(fill="both",expand=True)
        for i,(k,v) in enumerate(fields.items()):
            c=(i//12)*2;r=i%12
            ttk.Label(body,text=k.replace("_"," ")).grid(row=r,column=c,sticky="w",padx=4,pady=2)
            ttk.Entry(body,textvariable=v,width=26).grid(row=r,column=c+1,sticky="ew",padx=4)
        ttk.Label(win,text='Vectors: [x,y,z]. Fog volumes: [{"center":[0,0,0],"radius":8,"density":0.08}]').pack(padx=8)
        def apply_fx():
            nonlocal custom_fx,local_fx,extra_volumes,settings
            try:
                raw={k:json.loads(v.get()) for k,v in fields.items()}
                custom={k:tuple(raw[k]) if k in ("sun_color","fog_color") else raw[k] for k in keys}
                local={k:tuple(raw["local_"+k]) if k in ("color","direction") else raw["local_"+k] for k in ("color","intensity","radius","cone","direction")}
                volumes=tuple(FogVolume(center=tuple(v["center"]),radius=v["radius"],density=v["density"]) for v in raw["fog_volumes"])
                LocalLight(**local).validate()
                replace(base,**custom,fog_volumes=volumes).validate()
                next_settings=replace(settings,light=tuple(raw["sun_direction"])).validate()
            except (ValueError,TypeError,KeyError,AttributeError) as exc:
                messagebox.showerror("Lighting",str(exc),parent=win);return
            custom_fx=custom;local_fx=local;extra_volumes=volumes;settings=next_settings
            win.destroy();draw()
        def reset_fx():
            nonlocal custom_fx,local_fx,extra_volumes
            custom_fx={};local_fx={};extra_volumes=();win.destroy();draw()
        buttons=ttk.Frame(win);buttons.pack(fill="x",padx=8,pady=8)
        ttk.Button(buttons,text="Apply overrides",command=apply_fx).pack(side="left")
        ttk.Button(buttons,text="Reset to preset",command=reset_fx).pack(side="left")
    ttk.Button(fxbar,text="Advanced lighting",command=advanced_lighting).pack(side="left")
    def tick_water():
        if parent.winfo_exists():
            if water_enabled.get() and backend.get()=="Panda3D":draw()
            parent.after(150,tick_water)
    parent.after(150,tick_water)
    for label,cmd in [("Open scene",open_scene),("Save scene",save_scene),("Import OBJ",import_mesh),("Fit",fit),("Add tree",add),("Delete",delete),("Undo",lambda:(scene.undo(),sync())),("Redo",lambda:(scene.redo(),sync()))]:
        ttk.Button(toolbar,text=label,command=cmd).pack(side="left")
    ttk.Button(side,text="Apply transform",command=apply).pack(fill="x")
    objects.bind("<<ListboxSelect>>",select);canvas.bind("<Button-1>",pick);canvas.bind("<Button-3>",start);canvas.bind("<B3-Motion>",orbit)
    canvas.bind("<MouseWheel>",lambda e:zoom(e.delta));canvas.bind("<Button-4>",lambda e:zoom(1));canvas.bind("<Button-5>",lambda e:zoom(-1))
    canvas.bind("<Button-2>",pan_start);canvas.bind("<B2-Motion>",pan_move);canvas.bind("<ButtonRelease-2>",pan_end)
    canvas.bind("<Configure>",lambda e:draw());sync()
    def load_cell_preview(candidate, report, focus=None, on_select=None, on_stream=None):
        nonlocal scene,materials,camera,selected,native_preview,selection_callback,stream_callback,preview_origin,preview_cell
        if not native_preview and not messagebox.askyesno("Cell preview", "Replace the current portable viewport scene? Save any edits first.",parent=parent):
            return False
        scene=candidate;materials={};native_preview=True;selection_callback=on_select;stream_callback=on_stream;preview_origin=report["origin_game_units"];preview_cell=report["cell"]
        selected=focus if any(i.id==focus for i in scene.instances) else None
        camera=Camera()
        apply_world_environment(report)
        source.set(f"Read-only cell {report['cell']} | {report['cells']} cells | {report['land_tiles']} LAND tiles | {report.get('model_references',0)} models | {report['proxy_references']} reference markers | {report['skipped_references']} skipped")
        sync();parent.after_idle(fit)
        return True
    def drop_position(root_x,root_y):
        """Inverse orthographic projection onto camera focus-height plane."""
        if not native_preview or not canvas.winfo_viewable():return None
        px=root_x-canvas.winfo_rootx();py=root_y-canvas.winfo_rooty()
        w,h=canvas.winfo_width(),canvas.winfo_height()
        if not 0<=px<w or not 0<=py<h:return None
        from math import radians,sin,cos
        a,b=radians(camera.yaw),radians(camera.pitch)
        if abs(sin(b))<.05:return None
        right=(px-w/2)/camera.zoom
        forward=(py-h/2)/(camera.zoom*sin(b))
        x,y,z=camera.center
        return preview_cell,(128*(x+cos(a)*right+sin(a)*forward)+preview_origin[0],
            128*(y-sin(a)*right+cos(a)*forward)+preview_origin[1],
            128*z+preview_origin[2])
    def camera_command(action):
        nonlocal camera
        if action=="viewport-fit":fit();return
        if action=="viewport-zoom-in":zoom(1);return
        if action=="viewport-zoom-out":zoom(-1);return
        if action=="viewport-show":draw();return
        if action not in ("viewport-left","viewport-right","viewport-up","viewport-down"):raise ValueError("unsupported camera action")
        yaw=camera.yaw+({"viewport-left":-15,"viewport-right":15}.get(action,0))
        pitch=max(-85,min(85,camera.pitch+({"viewport-up":15,"viewport-down":-15}.get(action,0))))
        camera=replace(camera,yaw=yaw,pitch=pitch);draw()
    load_cell_preview.camera_command=camera_command
    load_cell_preview.drop_position=drop_position
    def drop_json(path):
        from tkinter import messagebox
        choice=messagebox.askyesnocancel("Import JSON","Open as a scene? Choose No for a material manifest.",parent=parent)
        if choice is True:open_scene(path)
        elif choice is False:import_materials(path)
    from .drop_import import editor_drop
    editor_drop(parent,[((".json",),drop_json,False),((".obj",),import_mesh,False)],target=canvas)
    return load_cell_preview
