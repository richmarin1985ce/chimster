"""Desktop record project authoring and side-by-side revision inspection."""
import json,tkinter as tk
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from .record_project import export,remove,KINDS
from .formids import staged_build
from .record_editor import inspect
from .plugin_compare import compare
DEFAULTS={"GMST":{"value":0},"GLOB":{"kind":"f","value":0.},"FACT":{"title":"Faction"},"MISC":{"title":"Item","model":"item.nif","bounds":[0,0,0,1,1,1],"value":0,"weight":0.},"STAT":{"model":"object.nif","bounds":[0,0,0,1,1,1]},"FLST":{"entries":[]}}
DEFAULTS.update({
 "REPU":{"title":"Reputation","value":100},
 "CONT":{"title":"Container","model":"container.nif","bounds":[0,0,0,1,1,1],"items":[]},
 "LVLI":{"entries":[{"ref":"ItemID","level":1,"count":1}]},
 "LVLN":{"entries":[{"ref":"ActorID","level":1,"count":1}]},
 "AMMO":{"title":"Ammunition","model":"ammo.nif","bounds":[0,0,0,1,1,1],"value":1,"weight":0.1,"speed":1,"clip_rounds":1,"projectile":{"plugin":"Source.esm","id":2048}},
 "ECZN":{"minimum_level":1},
 "VTYP":{"default_dialogue":False,"female":False},
 "CLAS":{"title":"Class","description":"","tag_skills":[32,37,43,-1],"special":[5]*7},
 "KEYM":{"title":"Key","model":"key.nif","bounds":[0,0,0,1,1,1],"value":0,"weight":0,"icon":"key.dds"},
 "SPEL":{"title":"Ability","type":4,"effects":[{"ref":"EffectID","magnitude":1,"area":0,"duration":0,"range":0,"actor_value":16}]},
 "PERK":{"title":"Perk","description":"","ranks":1,"minimum_level":1,"effects":[{"kind":"ability","ref":"AbilityID","rank":0,"priority":0}]},
 "ALCH":{"title":"Consumable","model":"food.nif","bounds":[0,0,0,1,1,1],"value":1,"weight":0.1,"equipment_type":12,"food":True,"effects":[{"ref":"EffectID","magnitude":1,"area":0,"duration":1,"range":0,"actor_value":16}]},
})
for k in ("NPC_","WEAP","ARMO","RACE","PACK","MGEF"):
    DEFAULTS[k]={"template":{"plugin":"Source.esm","id":2048}}
def mount(parent):
    bar=ttk.Frame(parent);bar.pack(fill="x")
    editor=tk.Text(parent,wrap="none");editor.pack(fill="both",expand=True)
    editor.insert("1.0",json.dumps({"schema":1,"records":[{"id":"ExampleGlobal","type":"GLOB","fields":DEFAULTS["GLOB"]}]},indent=2))
    def project():return json.loads(editor.get("1.0","end-1c"))
    def set_project(p):editor.delete("1.0","end");editor.insert("1.0",json.dumps(p,indent=2))
    def add():
        try:
            kind=simpledialog.askstring("Record type"," / ".join(KINDS))
            if not kind:return
            if kind not in DEFAULTS:raise ValueError("unknown record type")
            id=simpledialog.askstring("Record","Editor ID")
            if not id:return
            from .quest_editor import check_id
            p=project()
            if not check_id(id) or any(r["id"].casefold()==id.casefold() for r in p["records"]):raise ValueError("invalid or duplicate ID")
            p["records"].append({"id":id,"type":kind,"fields":DEFAULTS[kind]});set_project(p)
        except (ValueError,KeyError,TypeError) as e:messagebox.showerror("Record project",str(e))
    def delete():
        id=simpledialog.askstring("Remove draft record","Editor ID (does not delete any existing plugin record)")
        if not id:return
        try:set_project(remove(project(),id))
        except (ValueError,KeyError,TypeError) as e:messagebox.showerror("Record project",str(e))
    def open_project():
        p=filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if p:
            try:
                from .quest_editor import load
                set_project(load(p))
            except (OSError,ValueError) as e:messagebox.showerror("Record project",str(e))
    def save_project():
        p=filedialog.asksaveasfilename(defaultextension=".json")
        if p:
            try:
                with Path(p).open("x",encoding="utf-8") as f:json.dump(project(),f,indent=2)
            except (OSError,ValueError) as e:messagebox.showerror("Record project",str(e))
    def build_project():
        try:
            p=filedialog.asksaveasfilename(defaultextension=".esp")
            if not p:return
            previous=filedialog.askopenfilename(title="Previous FormID ledger (Cancel for new project)",filetypes=[("JSON","*.json")])
            ledger=p+".formids.json"
            spec=project();masters=[]
            while messagebox.askyesno("Dependencies","Add the next dependency in load order?"):
                dep=filedialog.askopenfilename(filetypes=[("Plugins","*.esm *.esp")])
                if not dep:return
                masters.append(dep)
            result=staged_build(lambda ids:export(spec,p,masters,ids),p,ledger,previous or None)
            messagebox.showinfo("Record project",json.dumps(result,indent=2))
        except (OSError,ValueError,KeyError,TypeError) as e:messagebox.showerror("Record project",str(e))
    def compare_ui():
        a=filedialog.askopenfilename(title="Original plugin")
        if not a:return
        b=filedialog.askopenfilename(title="Revised plugin (same filename)")
        if not b:return
        try:
            if Path(a).name.casefold()!=Path(b).name.casefold():raise ValueError("revision comparison requires same plugin name")
            report=compare(a,b)
            w=tk.Toplevel(parent);w.title("Record comparison");w.geometry("950x580")
            rows=report["changed"];lst=tk.Listbox(w,height=8);lst.pack(fill="x")
            for r in rows:lst.insert("end",f'{r["origin"]} {r["local_id"]:06X} {r["signature_after"]}')
            ttk.Label(w,text=f'Added: {len(report["added"])} | Removed: {len(report["removed"])} | Changed: {len(rows)}').pack(fill="x")
            pane=ttk.Panedwindow(w,orient="horizontal");pane.pack(fill="both",expand=True)
            left=tk.Text(pane,wrap="none");right=tk.Text(pane,wrap="none");pane.add(left,weight=1);pane.add(right,weight=1)
            def selected(e=None):
                if not lst.curselection():return
                r=rows[lst.curselection()[0]]
                for path,view in ((a,left),(b,right)):
                    view.delete("1.0","end")
                    try:view.insert("1.0",json.dumps(inspect(path,r["origin"],r["local_id"]),indent=2))
                    except (ValueError,OSError) as e:view.insert("1.0",str(e))
            lst.bind("<<ListboxSelect>>",selected)
        except (ValueError,OSError) as e:messagebox.showerror("Record comparison",str(e))
    for label,fn in (("Open",open_project),("Save draft",save_project),("Add record",add),("Remove draft record",delete),("Build ESP + ledger",build_project),("Compare plugins",compare_ui)):
        ttk.Button(bar,text=label,command=fn).pack(side="left")
