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
