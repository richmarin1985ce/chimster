"""Native file drop integration with ordinary Tk fallback."""
from pathlib import Path
import json
import tkinter as tk
from . import audio, phoneme_import as pi, morph_calibration as mc

def root():
    try:
        from tkinterdnd2 import TkinterDnD
    except ImportError:
        return tk.Tk()
    try:return TkinterDnD.Tk()
    except (RuntimeError,tk.TclError):
        old=tk._default_root
        if old is not None:old.destroy()
        return tk.Tk()

def bind_files(widget,callback,on_error):
    try:
        from tkinterdnd2 import DND_FILES
        widget.drop_target_register(DND_FILES)
        def dropped(event):
            try:callback([Path(p) for p in widget.tk.splitlist(event.data)])
            except Exception as exc:on_error(str(exc));return "refuse_drop"
            return "copy"
        widget.dnd_bind("<<Drop>>",dropped)
        return True
    except (ImportError,AttributeError,RuntimeError,tk.TclError):return False

def classify(paths):
    paths=list(map(Path,paths))
    if not paths or len(paths)>3:raise ValueError("Drop up to one WAV, timeline and profile")
    result={}
    for p in paths:
        if not p.is_file() or p.is_symlink():raise ValueError("Drop local regular files only")
        ext=p.suffix.lower()
        if ext==".wav":kind="wav"
        elif ext in (".csv",".tsv",".textgrid"):kind="timeline"
        elif ext==".json":
            if p.stat().st_size>16*1024*1024:raise ValueError("JSON too large")
            obj=json.loads(p.read_text(encoding="utf-8-sig"))
            kind="profile" if isinstance(obj,dict) and "observations" in obj else "timeline"
        else:raise ValueError("Unsupported file: "+p.name)
        if kind in result:raise ValueError("Multiple "+kind+" files in one drop")
        result[kind]=p
    return result

def load_bundle(paths,current,*,tier="phones"):
    found=classify(paths);state=dict(current)
    if "wav" in found:
        p=found["wav"]
        if p.stat().st_size>128*1024*1024:raise ValueError("WAV exceeds import limit")
        state.update(wav=str(p),duration=audio.wav_info(p.read_bytes())["duration"],rows=[])
    if "timeline" in found:
        if not state.get("duration"):raise ValueError("Open or drop a WAV first")
        state["rows"]=pi.load(found["timeline"],state["duration"],tier)
    if "profile" in found:
        state["profile"]=mc.profile(json.loads(found["profile"].read_text(encoding="utf-8-sig")))
    return state


def editor_drop(parent, routes, *, confirm=True, target=None):
    """Register an editor's actual import actions; never invoke export or tools.
    routes: [(extensions, callback, multiple)] with '<directory>' for folders.
    """
    from tkinter import ttk,messagebox
    def receive(paths):
        if not paths or len(paths)>128:raise ValueError("Drop 1–128 local files")
        kinds=[]
        for path in paths:
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise ValueError("Only local regular files or folders are accepted")
            kinds.append("<directory>" if path.is_dir() else path.suffix.lower())
        matches=[(callback,multi) for extensions,callback,multi in routes if all(k in extensions for k in kinds) and (multi or len(paths)==1)]
        if len(matches)!=1:raise ValueError("Drop one supported file type; use Browse for other imports")
        if confirm and not messagebox.askyesno("Import files","Open "+", ".join(p.name for p in paths[:5])+(" …" if len(paths)>5 else "")+" in this editor? Unsaved editor changes may be replaced.",parent=parent):return
        callback,multi=matches[0]
        callback(tuple(str(p) for p in paths) if multi else str(paths[0]))
    def error(msg):messagebox.showerror("File import",msg,parent=parent)
    label=ttk.Label(parent,text="Drop files here: "+", ".join(sorted({e for extensions,_,_ in routes for e in extensions})),relief="groove",padding=5)
    if bind_files(label,receive,error):
        label.pack(fill="x",side="bottom")
        if target is not None:bind_files(target,receive,error)
        return True
    label.destroy()
    return False


def path_field(widget, variable, extensions=None, *, directory=False):
    """Set an explicit input field, never launch a tool or write output."""
    from tkinter import messagebox
    def receive(paths):
        if len(paths)!=1:raise ValueError("Drop exactly one path")
        p=paths[0]
        if p.is_symlink():raise ValueError("Symbolic links are not accepted")
        if directory:
            if not p.is_dir():raise ValueError("Drop a directory")
        elif not p.is_file() or extensions is not None and p.suffix.lower() not in extensions:
            raise ValueError("Unsupported input file")
        variable.set(str(p))
    return bind_files(widget,receive,lambda msg:messagebox.showerror("Input path",msg,parent=widget))
