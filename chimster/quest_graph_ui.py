"""Visual quest graph pane: select, create, edit and connect stages."""
import tkinter as tk
from tkinter import ttk,simpledialog,messagebox
from collections import deque
from .quest_editor import check_id
def mount(parent,get_project,set_project):
    win=tk.Toplevel(parent);win.title("Quest graph");win.geometry("900x560")
    bar=ttk.Frame(win);bar.pack(fill="x")
    canvas=tk.Canvas(win,bg="#20262d",scrollregion=(0,0,900,600));canvas.pack(fill="both",expand=True)
    selected=None;project=None
    def refresh():
        nonlocal project,selected
        try:
            project=get_project()
            nodes={n["id"]:n for n in project["nodes"]}
            if len(nodes)!=len(project["nodes"]) or project["start"] not in nodes:raise ValueError("invalid stage IDs or start")
        except (ValueError,KeyError,TypeError) as e:messagebox.showerror("Quest graph",str(e));return
        if selected not in nodes:selected=None
        canvas.delete("all")
        depth={project["start"]:0};q=deque(depth)
        while q:
            k=q.popleft()
            for e in nodes[k].get("choices",[]):
                t=e["target"]
                if t in nodes and t not in depth:depth[t]=depth[k]+1;q.append(t)
        groups={}
        for k in nodes:groups.setdefault(depth.get(k,max(depth.values())+1),[]).append(k)
        pos={}
        for d,ids in sorted(groups.items()):
            for i,k in enumerate(ids):pos[k]=(30+d*210,40+i*100)
        for k,n in nodes.items():
            x,y=pos[k]
            for e in n.get("choices",[]):
                if e["target"] not in pos:continue
                a,b=pos[e["target"]];canvas.create_line(x+165,y+28,a,b+28,arrow="last",fill="#91a4b9",width=2)
        for k,(x,y) in pos.items():
            tag="node:"+k
            canvas.create_rectangle(x,y,x+165,y+56,fill="#435d70" if k==selected else "#35404b",outline="#b6cedf",tags=(tag,))
            canvas.create_text(x+8,y+10,text=k,fill="white",anchor="nw",tags=(tag,))
            canvas.create_text(x+8,y+30,text=nodes[k]["text"][:24],fill="#ccd7e0",anchor="nw",tags=(tag,))
            canvas.tag_bind(tag,"<Button-1>",lambda e,id=k:select(id))
        canvas.configure(scrollregion=canvas.bbox("all") or (0,0,900,600))
    def select(id):
        nonlocal selected
        selected=id;refresh()
    def commit():set_project(project);refresh()
    def add():
        nonlocal selected
        if project is None:return
        id=simpledialog.askstring("New stage","Unique stage ID",parent=win)
        if not id:return
        if not check_id(id) or any(n["id"]==id for n in project["nodes"]):messagebox.showerror("Quest graph","Invalid or duplicate stage ID");return
        text=simpledialog.askstring("New stage","Stage text",parent=win)
        if text is None:return
        project["nodes"].append({"id":id,"text":text,"choices":[]});selected=id;commit()
    def edit():
        if selected is None:return
        node=next(n for n in project["nodes"] if n["id"]==selected)
        value=simpledialog.askstring("Edit stage","Stage text",initialvalue=node["text"],parent=win)
        if value is not None:node["text"]=value;commit()
    def connect():
        if selected is None:return
        node=next(n for n in project["nodes"] if n["id"]==selected)
        target=simpledialog.askstring("Connect stage","Target stage ID",parent=win)
        if not target:return
        if target not in {n["id"] for n in project["nodes"]}:messagebox.showerror("Quest graph","Unknown target");return
        id=simpledialog.askstring("Connect stage","Unique choice ID",parent=win)
        if not id:return
        if not check_id(id) or any(e["id"]==id for e in node.get("choices",[])):messagebox.showerror("Quest graph","Invalid or duplicate choice ID");return
        text=simpledialog.askstring("Connect stage","Choice text",parent=win)
        if text is not None:node.setdefault("choices",[]).append({"id":id,"text":text,"target":target});commit()
    for label,fn in (("Refresh",refresh),("Add stage",add),("Edit selected",edit),("Connect selected",connect)):ttk.Button(bar,text=label,command=fn).pack(side="left")
    sb=ttk.Scrollbar(win,orient="horizontal",command=canvas.xview);sb.pack(fill="x");canvas.configure(xscrollcommand=sb.set)
    canvas.bind("<MouseWheel>",lambda e:canvas.yview_scroll(-1 if e.delta>0 else 1,"units"))
    refresh()
