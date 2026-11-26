"""Local desktop shell; no network or external executables."""
import json, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .core import PROFILES, catalog, inspect_plugin, plan

def launch():
 root=tk.Tk(); root.title('CHIMSTER | Bethesda Modding Workshop'); root.geometry('1000x650')
 root.configure(bg='#20252c'); style=ttk.Style(root); style.theme_use('clam')
 top=ttk.Frame(root,padding=12); top.pack(fill='x'); ttk.Label(top,text='CHIMSTER',font=('TkDefaultFont',20,'bold')).pack(side='left')
 game=tk.StringVar(value='newvegas'); ttk.Combobox(top,textvariable=game,values=list(PROFILES),state='readonly').pack(side='right')
 tabs=ttk.Notebook(root); tabs.pack(fill='both',expand=True,padx=12,pady=8)
 def tab(name):
  frame=ttk.Frame(tabs,padding=12); tabs.add(frame,text=name); return frame
 def output(frame):
  t=tk.Text(frame,wrap='word',bg='#1c2229',fg='#d6dce0',insertbackground='white'); t.pack(fill='both',expand=True,pady=8); return t
 def show(t,obj):
  t.delete('1.0','end'); t.insert('1.0',json.dumps(obj,indent=2,ensure_ascii=False))
 f=tab('Tool registry'); bar=ttk.Frame(f); bar.pack(fill='x'); out=output(f)
 def refresh(): show(out,[x for x in catalog() if '*' in x['games'] or game.get() in x['games']])
 ttk.Button(bar,text='Refresh for selected game',command=refresh).pack(side='left'); game.trace_add('write',lambda *_:refresh()); refresh()
 f=tab('Plugin inspector'); bar=ttk.Frame(f); bar.pack(fill='x'); io=output(f)
 def inspect():
  file=filedialog.askopenfilename(filetypes=[('Bethesda plugins','*.esp *.esm *.esl *.omwaddon *.omwgame'),('All files','*')]);
  if file:
   try: show(io,inspect_plugin(file,game.get()))
   except (OSError,ValueError) as e: messagebox.showerror('Inspection failed',str(e))
 ttk.Button(bar,text='Open plugin (read only)',command=inspect).pack(side='left')
 f=tab('Action planner'); ttk.Label(f,text='Describe a mod task. Template-based proposal; no AI backend connected.').pack(anchor='w'); entry=ttk.Entry(f); entry.pack(fill='x',pady=5); bar=ttk.Frame(f); bar.pack(fill='x'); po=output(f)
 def propose():
  try: show(po,plan(game.get(),entry.get()))
  except ValueError as e: messagebox.showerror('Planning failed',str(e))
 ttk.Button(bar,text='Create proposal',command=propose).pack(side='left')
 f=tab('OpenMW bridge'); ttk.Label(f,text='Use installed OpenMW tools. Editor uses its existing profile.').pack(anchor='w')
 bar=ttk.Frame(f); bar.pack(fill='x'); oo=output(f)
 from .openmw import discover, Profile, launch_game, launch_editor
 def choose_profile(run=False):
  file=filedialog.askopenfilename(filetypes=[('OpenMW profile JSON','*.json')])
  if not file: return
  try:
   profile=Profile.load(file)
   args=profile.engine_args()
   if run and messagebox.askyesno('Launch OpenMW','Launch with the selected test workspace and load order?'):
    show(oo,{'pid':launch_game(profile).pid,'arguments':args})
   else: show(oo,{'arguments':args})
  except (OSError,ValueError,KeyError,TypeError) as e: messagebox.showerror('OpenMW profile error',str(e))
 def editor():
  if not messagebox.askyesno('OpenMW-CS','Editor uses its existing configuration. Confirm that its data-local directory is your intended workspace. Continue?'): return
  try: show(oo,{'pid':launch_editor().pid,'profile':'installed editor default'})
  except (OSError,ValueError) as e: messagebox.showerror('Editor launch failed',str(e))
 ttk.Button(bar,text='Detect tools',command=lambda:show(oo,discover())).pack(side='left')
 ttk.Button(bar,text='Preview profile',command=choose_profile).pack(side='left')
 ttk.Button(bar,text='Launch game',command=lambda:choose_profile(True)).pack(side='left')
 ttk.Button(bar,text='Launch editor',command=editor).pack(side='left')
 root.mainloop()
