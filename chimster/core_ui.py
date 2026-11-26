"""Desktop core dependency and offline release management."""
import tkinter as tk,json
from tkinter import ttk,filedialog,messagebox,simpledialog
from pathlib import Path
from .dependencies import report,pin
from .app_releases import Installation
def mount(parent):
    config=tk.StringVar();root=tk.StringVar()
    bar=ttk.Frame(parent);bar.pack(fill="x")
    ttk.Label(bar,text="Dependency config").pack(side="left")
    ttk.Entry(bar,textvariable=config).pack(side="left",fill="x",expand=True)
    second=ttk.Frame(parent);second.pack(fill="x")
    ttk.Label(second,text="Install root").pack(side="left")
    ttk.Entry(second,textvariable=root).pack(side="left",fill="x",expand=True)
    out=tk.Text(parent,wrap="word");out.pack(fill="both",expand=True)
    def show(v):out.delete("1.0","end");out.insert("1.0",json.dumps(v,indent=2))
    def guard(fn):
        def run():
            try:fn()
            except (OSError,ValueError,KeyError,TypeError,RuntimeError) as e:messagebox.showerror("Core management",str(e))
        return run
    def choose_config():
        p=filedialog.asksaveasfilename(title="Dependency configuration",defaultextension=".json",confirmoverwrite=False)
        if p:config.set(p)
    def choose_root():
        p=filedialog.askdirectory(title="Local versioned application install root")
        if p:root.set(p)
    def deps():show(report(config.get() or None))
    def bind():
        if not config.get():raise ValueError("choose dependency config")
        tool=simpledialog.askstring("Dependency","Tool name (use the name from the dependency report)")
        if not tool:return
        p=filedialog.askopenfilename(title="Select a trusted local executable")
        if p and messagebox.askyesno("Pin executable","Pin the selected executable's current SHA-256? This does not execute it."):
            pin(config.get(),tool,p);deps()
    def installation():
        if not root.get():raise ValueError("choose installation root")
        return Installation(root.get())
    def install():
        i=installation();p=filedialog.askopenfilename(filetypes=[("Application ZIP","*.zip")])
        if not p:return
        sha=simpledialog.askstring("Trusted digest","SHA-256 from a separately trusted source")
        if not sha:return
        if messagebox.askyesno("Install version","Install this local archive without launching it?"):
            show(i.install(p,sha,False))
    def activate():
        i=installation();v=simpledialog.askstring("Activate version","Installed version")
        if v:show(i.activate(v))
    for label,fn in (("Choose",choose_config),("Inspect",deps),("Pin tool",bind)):
        ttk.Button(bar,text=label,command=guard(fn)).pack(side="left")
    for label,fn in (("Choose",choose_root),("Versions",lambda:show(installation().status())),("Install ZIP",install),("Activate / rollback",activate)):
        ttk.Button(second,text=label,command=guard(fn)).pack(side="left")
