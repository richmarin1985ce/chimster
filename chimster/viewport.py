"""Tk desktop viewport with an original portable scene model."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
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
    native_weather={};native_render={};starfield_preview=False;planet_stream=False
    native_lighting_enabled=tk.BooleanVar(value=True)
    native_day=tk.StringVar(value="Day")
    def draw():
        nonlocal renderer,panda,photo,render_size,failure
        canvas.delete("mesh");canvas.delete("gl")
        try:
            pos=tuple(float(x) for x in light_pos.get().split(","))
            lights=(LocalLight(position=pos,direction=local_fx.get("direction",(0,0,-1)) if spot_enabled.get() else None,shadows=spot_enabled.get(),**{k:v for k,v in local_fx.items() if k!="direction"}),) if point_enabled.get() else ()
            native_values={}
            if native_preview and native_lighting_enabled.get():
                from .native_render_records import select_lights
                native_values=native_render.get("effects",{})
                lights=lights+select_lights(native_render.get("lights",()),camera.center,4-len(lights))
                if sum(bool(l.shadows) for l in lights)>1:
                    first=next(i for i,l in enumerate(lights) if l.shadows)
                    lights=tuple(replace(l,shadows=False) if i!=first else l for i,l in enumerate(lights))
            render_settings=settings
            if native_preview and native_lighting_enabled.get() and native_render.get("planet_solar"):
                from .starfield_planets import solar_preview
                solar=native_render["planet_solar"]
                direction,diurnal=solar_preview(solar["latitude"],{"Dawn":6,"Day":12,"Dusk":18,"Night":0}.get(native_day.get(),12),atmosphere=solar.get("atmosphere"))
                native_values={**native_values,**diurnal}
                render_settings=replace(settings,light=direction)
            effects=replace(preset(effect_name.get()),water_level=float(water_height.get()) if water_enabled.get() else None,lights=lights,fog_volumes=extra_volumes,**{**weather_effects(),**native_values,**custom_fx}).validate()
        except ValueError as exc:
            status.set("Effects: "+str(exc));return
        if backend.get().startswith("Panda3D") and canvas.winfo_width()>4 and canvas.winfo_height()>4:
            try:
                from .panda_viewport import Preview
                from PIL import Image,ImageTk
                if panda is None:panda=Preview({"Panda3D":"native","Panda3D PBR":"pbr","Panda3D Filters":"filters"}[backend.get()])
                w,h=canvas.winfo_width(),canvas.winfo_height()
                factor=min(1,1280/w,720/h);rw,rh=max(1,int(w*factor)),max(1,int(h*factor))
                raw=panda.render(scene,replace(camera,zoom=camera.zoom*factor),rw,rh,materials,render_settings,effects)
                photo=ImageTk.PhotoImage(Image.frombytes("RGBA",(rw,rh),raw).resize((w,h)))
                canvas.create_image(0,0,image=photo,anchor="nw",tags=("gl",))
                status.set(backend.get()+(" | underwater native fog" if panda.underwater else " | water" if water_enabled.get() else "")+(" | post fallback: "+panda.post_error if panda.post_error else "")+(" | reflection fallback: "+panda.water_error if panda.water_error else ""))
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
                raw,stats=renderer.render(scene,scaled,rw,rh,materials,render_settings,selected,effects)
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
        nonlocal scene,selected,native_preview,starfield_preview
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Chimster scene","*.json")])
        if p:
            try:scene=Scene.load(p);selected=None;native_preview=False;starfield_preview=False;source.set("Portable scene");sync()
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
        p=dropped if dropped is not None else filedialog.askopenfilename(filetypes=[("Static mesh","*.obj *.mesh"),("Triangulated OBJ","*.obj"),("Starfield external mesh","*.mesh")])
        if p:
            try:
                lods=[]
                if Path(p).suffix.casefold()==".mesh":
                    from .starfield_mesh import load
                    m,lods,_=load(p)
                else:m=load_obj(p)
                n=1
                while f"import-{n}" in scene.assets:n+=1
                key=f"import-{n}";scene.assets[key]=m
                for i,lod in enumerate(lods,1):scene.assets[key+"@lod"+str(i)]=lod
                scene.add(Instance(key,key));selected=key;sync()
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
        nonlocal native_weather,native_render
        native_render=report.get("render_preview",{})
        native_weather=report.get("environment",{}).get("weather_preview") or {}
        # Native water level is a geometry height, not a material/engine simulation.
        env=report.get("environment",{}).get("values",{})
        heights=env.get("heights")
        if native_render:
            level=native_render.get("water_level")
            water_enabled.set(level is not None)
            if level is not None:water_height.set(str(level))
        elif report.get("grid") is not None and heights is not None:
            water_height.set(str(heights[1]/128))
            water_enabled.set("water" in env)
        else:water_enabled.set(False)
    def pan_end(e):
        nonlocal pan_drag,camera,scene,materials,selected,preview_origin,preview_cell
        pan_drag=None
        if not native_preview or stream_callback is None:return
        scale=1 if planet_stream else 128
        absolute=tuple(camera.center[i]*scale+preview_origin[i] for i in range(3))
        try:result=stream_callback(absolute[0],absolute[1])
        except (OSError,ValueError,TypeError,KeyError) as exc:
            status.set("Cell streaming: "+str(exc));return
        if result is None:return
        candidate,report=result
        scene=candidate;materials=dict(report.get("preview_materials",{}));preview_origin=report["origin_game_units"];preview_cell=report["cell"]
        camera=replace(camera,center=tuple((absolute[i]-preview_origin[i])/scale for i in range(3)))
        apply_world_environment(report)
        if not any(i.id==selected for i in scene.instances):selected=None
        if planet_stream:source.set(f"Starfield landing | {report['latitude']:.5f}, {report['longitude']:.5f} | {report['land_tiles']} tiles (illustrative)")
        else:source.set(f"Read-only cell {report['cell']} | {report['cells']} cells | {report['land_tiles']} LAND tiles | {report.get('model_references',0)} models")
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
    choice=ttk.Combobox(controls,textvariable=backend,values=("Panda3D","Panda3D PBR","Panda3D Filters","ModernGL","CPU"),state="readonly",width=18)
    choice.pack(side="left")
    def switch_backend(event=None):
        nonlocal renderer,panda,failure
        failure=""
        if panda is not None:
            try:panda.close()
            finally:panda=None
        if backend.get()!="ModernGL" and renderer is not None:
            try:renderer.close()
            finally:renderer=None
        draw()
    choice.bind("<<ComboboxSelected>>",switch_backend)
    def preview_glb():
        nonlocal panda,camera
        path=filedialog.askopenfilename(filetypes=[("Embedded glTF binary","*.glb")])
        if not path:return
        try:
            backend.set("Panda3D PBR");switch_backend()
            if panda is None:raise RuntimeError("Panda PBR unavailable")
            bounds=panda.set_glb_preview(path)
            if bounds:
                lo,hi=bounds;size=max(1,max(hi[k]-lo[k] for k in range(3)))
                camera=replace(camera,center=tuple((lo[k]+hi[k])/2 for k in range(3)),zoom=max(.05,min(2000,min(canvas.winfo_width(),canvas.winfo_height())*.65/size)))
            draw()
            status.set(status.get()+" | GLB preview only; not saved to scene")
        except Exception as e:messagebox.showerror("GLB preview",str(e))
    def bake_probe():
        if panda is None or backend.get()!="Panda3D PBR":
            messagebox.showinfo("Reflection probes","Select Panda3D PBR and render a scene first.");return
        radius=simpledialog.askfloat("Reflection probe","Influence radius in scene units",initialvalue=20,minvalue=.1,maxvalue=10000,parent=parent)
        if radius is None:return
        try:
            panda.bake_probe(camera.center,radius);draw()
            status.set(status.get()+f" | {len(panda.probes)} probes / {panda.probe_count} affected objects")
        except Exception as e:messagebox.showerror("Reflection probe",str(e))
    def clear_probes():
        if panda is not None:panda.clear_probes();draw()
    ttk.Button(side,text="Bake reflection probe at view center",command=bake_probe).pack(fill="x")
    def save_probes():
        if panda is None:return
        path=filedialog.asksaveasfilename(parent=parent,defaultextension=".probes.json",filetypes=[("Probe snapshots","*.probes.json")])
        if path:
            try:panda.save_probes(path)
            except Exception as e:messagebox.showerror("Save reflection probes",str(e))
    def load_probes():
        if panda is None or backend.get()!="Panda3D PBR":
            messagebox.showinfo("Reflection probes","Select Panda3D PBR first.");return
        path=filedialog.askopenfilename(parent=parent,filetypes=[("Probe snapshots","*.probes.json"),("JSON","*.json")])
        if path:
            try:panda.load_probes(path);draw()
            except Exception as e:messagebox.showerror("Load reflection probes",str(e))
    ttk.Button(side,text="Clear reflection probes",command=clear_probes).pack(fill="x")
    ttk.Button(side,text="Save reflection probes",command=save_probes).pack(fill="x")
    ttk.Button(side,text="Load reflection probes",command=load_probes).pack(fill="x")
    def clear_glb():
        if panda is not None:panda.set_glb_preview();draw()
    ttk.Button(side,text="Preview embedded GLB",command=preview_glb).pack(fill="x")
    ttk.Button(side,text="Clear GLB preview",command=clear_glb).pack(fill="x")
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
    ttk.Checkbutton(fxbar,text="Native lighting",variable=native_lighting_enabled,command=draw).pack(side="left")
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
    day_choice=ttk.Combobox(fxbar,textvariable=native_day,values=("Dawn","Day","Dusk","Night"),state="readonly",width=6)
    day_choice.pack(side="left");day_choice.bind("<<ComboboxSelected>>",lambda e:draw())
    def advanced_lighting():
        nonlocal custom_fx,local_fx,extra_volumes,settings
        import json
        win=tk.Toplevel(parent);win.title("Lighting and atmospheric controls")
        ttk.Label(win,text="ModernGL: nested shadow maps and volumetric lighting. Panda: native lights, shadows, distance fog.").pack(padx=8,pady=6)
        base=preset(effect_name.get())
        keys=("ambient","sun_intensity","sun_color","environment_strength","shadow_size","shadow_extent","shadow_cascades","shadow_bias","fog_density","fog_color","fog_height","fog_falloff","scatter_strength","scatter_anisotropy","volume_steps","volume_distance","water_color","water_deep_color","water_opacity","water_reflectivity","water_absorption","water_foam","underwater_density","ssr_strength","ssr_steps","ssr_distance")
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
                custom={k:tuple(raw[k]) if k in ("sun_color","fog_color","water_color","water_deep_color") and raw[k] is not None else raw[k] for k in keys}
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
            if water_enabled.get() and backend.get().startswith("Panda3D"):draw()
            parent.after(150,tick_water)
    parent.after(150,tick_water)
    for label,cmd in [("Open scene",open_scene),("Save scene",save_scene),("Import mesh",import_mesh),("Fit",fit),("Add tree",add),("Delete",delete),("Undo",lambda:(scene.undo(),sync())),("Redo",lambda:(scene.redo(),sync()))]:
        ttk.Button(toolbar,text=label,command=cmd).pack(side="left")
    ttk.Button(side,text="Apply transform",command=apply).pack(fill="x")
    objects.bind("<<ListboxSelect>>",select);canvas.bind("<Button-1>",pick);canvas.bind("<Button-3>",start);canvas.bind("<B3-Motion>",orbit)
    canvas.bind("<MouseWheel>",lambda e:zoom(e.delta));canvas.bind("<Button-4>",lambda e:zoom(1));canvas.bind("<Button-5>",lambda e:zoom(-1))
    canvas.bind("<Button-2>",pan_start);canvas.bind("<B2-Motion>",pan_move);canvas.bind("<ButtonRelease-2>",pan_end)
    canvas.bind("<Configure>",lambda e:draw());sync()
    def load_cell_preview(candidate, report, focus=None, on_select=None, on_stream=None):
        nonlocal scene,materials,camera,selected,native_preview,selection_callback,stream_callback,preview_origin,preview_cell,starfield_preview,planet_stream
        if not native_preview and not messagebox.askyesno("Cell preview", "Replace the current portable viewport scene? Save any edits first.",parent=parent):
            return False
        scene=candidate;materials=dict(report.get("preview_materials",{}));native_preview=True;starfield_preview=bool(report.get("starfield"));planet_stream=bool(report.get("planet_stream"));selection_callback=on_select;stream_callback=on_stream;preview_origin=report["origin_game_units"];preview_cell=report["cell"]
        selected=focus if any(i.id==focus for i in scene.instances) else None
        camera=Camera()
        apply_world_environment(report)
        source.set(f"Read-only cell {report['cell']} | {report['cells']} cells | {report['land_tiles']} LAND tiles | {report.get('model_references',0)} models | {report['proxy_references']} reference markers | {report['skipped_references']} skipped")
        sync();parent.after_idle(fit)
        return True
    def drop_position(root_x,root_y):
        """Inverse orthographic projection onto camera focus-height plane."""
        if not native_preview or starfield_preview or not canvas.winfo_viewable():return None
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
    def open_starfield():
        from .starfield_preview import Catalog,label
        paths=filedialog.askopenfilenames(parent=parent,title="Select full Starfield masters and plugins in load order",filetypes=[("Starfield plugins","*.esm *.esp"),("All files","*")])
        if not paths:return
        try:
            catalog=Catalog(paths)
            query=simpledialog.askstring("Starfield cell","Filter cells by editor ID or plugin:local FormID",parent=parent)
            if query is None:return
            choices=catalog.choices(query)
            if not choices:raise ValueError("No matching cells")
            win=tk.Toplevel(parent);win.title("Select Starfield cell (experimental)")
            rows=tk.Listbox(win,width=72,height=18,exportselection=False);rows.pack(fill="both",expand=True)
            for key,name in choices:rows.insert("end",label(key)+"  "+name)
            def choose():
                ids=rows.curselection()
                if not ids:return
                units=simpledialog.askfloat("Preview scale","Game units per preview unit",initialvalue=1.,minvalue=.001,maxvalue=10000,parent=win)
                if units is None:return
                try:
                    from .starfield_mesh import MappedMeshes
                    mapped=None
                    if messagebox.askyesno("Starfield native geometry","Load NIF and external mesh geometry directly from BA2 archives or loose Data?",parent=win):
                        from .starfield_assets import Sources
                        from .starfield_nif import AutoMeshes
                        archives=filedialog.askopenfilenames(parent=win,title="Select BA2 archives in low-to-high priority",filetypes=[("BA2 archives","*.ba2")])
                        loose=filedialog.askdirectory(parent=win,title="Optional loose Data directory")
                        if archives or loose:
                            sources=Sources(archives,loose)
                            from .starfield_materials import NativeMaterials
                            preview_materials=NativeMaterials(None,sources)
                            if messagebox.askyesno("Starfield material preview","Use an optional .mat-to-texture preview mapping?",parent=win):
                                from .starfield_materials import NativeMaterials
                                material_map=filedialog.askopenfilename(parent=win,filetypes=[("Preview material mapping","*.json")])
                                if material_map:preview_materials=NativeMaterials(material_map,sources)
                            bind_pose=messagebox.askyesno("Static character preview","Include skinned geometry in its undeformed bind pose? No animation or bone transforms are applied.",parent=win)
                            mapped=AutoMeshes(sources,units,materials=preview_materials,bind_pose=bind_pose)
                    elif messagebox.askyesno("Starfield geometry","Use an optional NIF-to-.mesh manifest for native static geometry?",parent=win):
                        manifest=filedialog.askopenfilename(parent=win,filetypes=[("Mesh manifest","*.json")])
                        if manifest:
                            from .starfield_assets import Sources
                            sources=None
                            if messagebox.askyesno("Starfield archives","Read manifest geometry from game BA2 archives or loose Data?",parent=win):
                                archives=filedialog.askopenfilenames(parent=win,title="Select BA2 archives in low-to-high priority",filetypes=[("BA2 archives","*.ba2")])
                                loose=filedialog.askdirectory(parent=win,title="Optional loose Data directory (Cancel for archives only)")
                                sources=Sources(archives,loose)
                            mapped=MappedMeshes(manifest,units,sources)
                    scene,report=catalog.preview(choices[ids[0]][0],units,mapped)
                    if load_cell_preview(scene,report):
                        source.set("Starfield experimental | "+report["cell"]+" | "+str(report["light_records"])+" lights | "+str(report["model_references"])+" mapped models | "+str(report["proxy_references"])+" proxies")
                        win.destroy()
                except Exception as exc:messagebox.showerror("Starfield preview",str(exc),parent=win)
            ttk.Button(win,text="Open read-only preview",command=choose).pack()
        except Exception as exc:messagebox.showerror("Starfield preview",str(exc),parent=parent)
    ttk.Button(toolbar,text="Starfield cell preview",command=open_starfield).pack(side="left")
    def open_planets():
        from .starfield_planets import Planets,globe,terrain,Heightfield,LandingStream,surface_summary,system_preview,export_heightfield
        from .starfield_preview import label
        paths=filedialog.askopenfilenames(parent=parent,title="Select Starfield full masters in load order",filetypes=[("Starfield plugins","*.esm *.esp")])
        if not paths:return
        try:
            catalog=Planets(paths)
            query=simpledialog.askstring("Planet browser","Filter by planet name or FormID",parent=parent)
            if query is None:return
            choices=catalog.choices(query)
            if not choices:raise ValueError("No matching planets")
            win=tk.Toplevel(parent);win.title("Starfield planets — experimental")
            rows=tk.Listbox(win,width=72,height=18,exportselection=False);rows.pack(fill="both",expand=True)
            for k,p in choices:rows.insert("end",p["name"]+" | "+label(k)+" | radius "+str(p.get("radius_km","unknown"))+" km")
            info=tk.StringVar(value="Select a body. Geography is illustrative.");ttk.Label(win,textvariable=info,wraplength=550).pack()
            def chosen():
                ids=rows.curselection()
                return choices[ids[0]] if ids else (None,None)
            def update(e=None):
                k,p=chosen()
                if p:info.set(f"{p['name']} | {len(p['biomes'])} biome links | {len(p['worldspaces'])} worldspaces | gravity {p.get('gravity','unknown')} | temperature {p.get('temperature','unknown')} C")
            rows.bind("<<ListboxSelect>>",update)
            def preview(local):
                k,p=chosen()
                if k is None:return
                try:
                    stream=None
                    if local:
                        lat=simpledialog.askfloat("Landing latitude","Latitude in degrees",initialvalue=0,minvalue=-90,maxvalue=90,parent=win)
                        if lat is None:return
                        lon=simpledialog.askfloat("Landing longitude","Longitude in degrees",initialvalue=0,minvalue=-180,maxvalue=180,parent=win)
                        if lon is None:return
                        span=simpledialog.askfloat("Landing width","Area width in kilometers",initialvalue=8,minvalue=.1,maxvalue=100,parent=win)
                        if span is None:return
                        heights=None;native_btd=False
                        if messagebox.askyesno("Landing heightfield","Use a user-supplied square JSON heightfield in meters instead of illustrative terrain?",parent=win):
                            heightpath=filedialog.askopenfilename(parent=win,filetypes=[("Heightfield JSON","*.json")])
                            if heightpath:heights=Heightfield.load(heightpath)
                        if heights is None and messagebox.askyesno("Native terrain","Preview a local Starfield .btd terrain file instead of generated relief?",parent=win):
                            from .starfield_btd import BTD
                            btdpath=filedialog.askopenfilename(parent=win,filetypes=[("Starfield terrain","*.btd")])
                            if btdpath:
                                btd=BTD.load(btdpath)
                                x=simpledialog.askinteger("BTD cell X","Southwest cell X",initialvalue=btd.min_cell[0],minvalue=btd.min_cell[0],maxvalue=btd.min_cell[0]+btd.nx-1,parent=win)
                                if x is None:return
                                y=simpledialog.askinteger("BTD cell Y","Southwest cell Y",initialvalue=btd.min_cell[1],minvalue=btd.min_cell[1],maxvalue=btd.min_cell[1]+btd.ny-1,parent=win)
                                if y is None:return
                                scale=simpledialog.askfloat("BTD height units","Meters per stored height unit (verify against game data)",initialvalue=1,minvalue=.0001,maxvalue=1000,parent=win)
                                if scale is None:return
                                heights=btd.heightfield(x,y,meters_per_height_unit=scale);native_btd=True
                        if heights is None:
                            stream=LandingStream(catalog,k,lat,lon,span)
                            candidate,report=stream.update()
                        else:
                            candidate,report=terrain(catalog,k,lat,lon,span,heightfield=heights)
                            if native_btd:report["height_source"]="native BTD samples (user scale)"
                    else:candidate,report=globe(catalog,k)
                    if load_cell_preview(candidate,report,on_stream=stream.update if stream else None):source.set("Starfield "+p["name"]+" | "+report.get("height_source","illustrative")+" "+report["planet_mode"]+" preview")
                except (ValueError,OSError,KeyError) as exc:messagebox.showerror("Planet preview",str(exc),parent=win)
            def inspect():
                k,p=chosen()
                if k is None:return
                lines=[f"{name or label(world)}: {lat:.5f}, {lon:.5f}" for world,lat,lon,name in catalog.sites(k) if world is not None]
                messagebox.showinfo("Worldspace landing sites (xEdit coordinate order; unverified)", "\\n".join(lines[:100]) or "No decoded sites",parent=win)
            ttk.Button(win,text="Globe preview",command=lambda:preview(False)).pack(fill="x")
            def orbit_view():
                k,p=chosen()
                if k is None:return
                candidate,report=system_preview(catalog,k)
                if load_cell_preview(candidate,report):source.set("Starfield | schematic system orbits")
            ttk.Button(win,text="System orbit preview",command=orbit_view).pack(fill="x")
            def export_raw():
                try:
                    src=filedialog.askopenfilename(parent=win,filetypes=[("Heightfield JSON","*.json")])
                    if not src:return
                    field=Heightfield.load(src)
                    dst=filedialog.asksaveasfilename(parent=win,defaultextension=".r32",filetypes=[("Raw float32 elevations","*.r32")])
                    if dst:export_heightfield(dst,field);messagebox.showinfo("Portable terrain export",f"{field.n} x {field.n} float32 samples; meters, south-to-north rows. Verify import orientation and scaling.",parent=win)
                except (OSError,ValueError) as exc:messagebox.showerror("Terrain export",str(exc),parent=win)
            ttk.Button(win,text="Export heightfield R32",command=export_raw).pack(fill="x")
            ttk.Button(win,text="Landing terrain preview",command=lambda:preview(True)).pack(fill="x")
            ttk.Button(win,text="Inspect native landing sites",command=inspect).pack(fill="x")
            def inspect_surface():
                k,p=chosen()
                if k is None:return
                try:
                    tree=p.get("tree")
                    if tree is None:raise ValueError("No linked surface tree")
                    row=catalog.surface_record(tree);summaries=surface_summary(row)
                    lines=[f"{row['name']} | {row['signature']} | filter: {row['filter']}"] if row else ["Missing linked surface record"]
                    for item in summaries:
                        lines.append(f"{item['tag']}: {item['side']} x {item['side']} | {item['unique']} distinct raw IDs | {item['nonzero']} occupied")
                        lines.extend(f"  {raw}: {count}" for raw,count in item["top"])
                    messagebox.showinfo("Native surface array inspection (raw IDs)", "\n".join(lines),parent=win)
                except (ValueError,OSError,KeyError) as exc:messagebox.showerror("Surface inspection",str(exc),parent=win)
            ttk.Button(win,text="Inspect native surface tree",command=inspect_surface).pack(fill="x")
            def inspect_climate():
                k,p=chosen()
                if k is None:return
                lines=[]
                for biome,chance in p["biomes"]:
                    b=catalog.biomes.get(biome,{})
                    climate=catalog.climates.get(b.get("climate"),{})
                    lines.append(f"{b.get('name','Unknown biome')} ({chance:g}) | {climate.get('name','No decoded climate')} | {len(climate.get('weather',[]))} weather entries | {len(climate.get('settings',[]))} settings")
                messagebox.showinfo("Native biome climates", "\n".join(lines[:100]) or "No biome climate links",parent=win)
            ttk.Button(win,text="Inspect biome climates",command=inspect_climate).pack(fill="x")
        except (ValueError,OSError,KeyError) as exc:messagebox.showerror("Planet browser",str(exc),parent=parent)
    ttk.Button(toolbar,text="Starfield planets",command=open_planets).pack(side="left")
    load_cell_preview.drop_position=drop_position
    def drop_json(path):
        from tkinter import messagebox
        choice=messagebox.askyesnocancel("Import JSON","Open as a scene? Choose No for a material manifest.",parent=parent)
        if choice is True:open_scene(path)
        elif choice is False:import_materials(path)
    from .drop_import import editor_drop
    editor_drop(parent,[((".json",),drop_json,False),((".obj",".mesh"),import_mesh,False)],target=canvas)
    return load_cell_preview
