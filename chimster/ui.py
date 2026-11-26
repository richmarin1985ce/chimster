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
 f=tab('Project')
 from .project_ui import mount as mount_project
 mount_project(f,game)
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
 f=tab('Landscape budget'); bar=ttk.Frame(f);bar.pack(fill='x'); budget_out=output(f)
 def inspect_budget():
  from .texture_budget import scan_land
  path=filedialog.askopenfilename(filetypes=[('Plugins','*.esp *.esm')])
  if path:
   try:
    r=scan_land(path,game.get())
    show(budget_out,r)
   except (OSError,ValueError) as e:messagebox.showerror('Landscape budget',str(e))
 ttk.Button(bar,text='Inspect quadrant allocations (read only)',command=inspect_budget).pack(side='left')
 f=tab('Record editor'); rb=ttk.Frame(f);rb.pack(fill='x')
 rp=tk.StringVar();ro=tk.StringVar();ri=tk.StringVar(value='0x800');rf=tk.StringVar(value='FULL');rv=tk.StringVar()
 def record_source():
  p=filedialog.askopenfilename(filetypes=[('Plugins','*.esp *.esm')])
  if p:
   from pathlib import Path
   rp.set(p);ro.set(Path(p).name)
 ttk.Button(rb,text='Source plugin',command=record_source).pack(side='left')
 ttk.Entry(rb,textvariable=rp).pack(side='left',fill='x',expand=True)
 fields=ttk.Frame(f);fields.pack(fill='x')
 for label,var in [('Origin',ro),('Local ID',ri),('Field',rf),('New value (JSON)',rv)]:
  ttk.Label(fields,text=label).pack(side='left');ttk.Entry(fields,textvariable=var,width=16).pack(side='left')
 actions=ttk.Frame(f);actions.pack(fill='x');record_out=output(f);record_state={}
 def read_record():
  from .record_editor import inspect
  try:
   r=inspect(rp.get(),ro.get(),int(ri.get(),0));record_state.clear()
   record_state.update(path=rp.get(),origin=ro.get(),id=int(ri.get(),0),hash=r['payload_sha256'])
   show(record_out,r)
  except (OSError,ValueError,KeyError) as e:messagebox.showerror('Record editor',str(e))
 def edit_record():
  from .record_editor import edit_typed
  from pathlib import Path
  try:
   if not record_state or (rp.get(),ro.get(),int(ri.get(),0))!=(record_state['path'],record_state['origin'],record_state['id']):raise ValueError('Inspect the current record first')
   d=filedialog.askdirectory(title='Choose staging directory (same plugin name, no overwrite)')
   if d:show(record_out,edit_typed(rp.get(),Path(d)/Path(rp.get()).name,ro.get(),int(ri.get(),0),rf.get(),json.loads(rv.get()),record_state['hash']))
  except (OSError,ValueError,KeyError) as e:messagebox.showerror('Record editor',str(e))
 ttk.Button(actions,text='Inspect record',command=read_record).pack(side='left')
 ttk.Button(actions,text='Save staged typed edit',command=edit_record).pack(side='left')
 f=tab('Record projects')
 from .record_project_ui import mount as record_project_mount
 record_project_mount(f)
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
 f=tab('Texture Forge'); ttk.Label(f,text='Generate normal/specular maps from explicit masks, or a six-face DDS cubemap.').pack(anchor='w')
 bar=ttk.Frame(f);bar.pack(fill='x')
 strength=tk.DoubleVar(value=4.0);convention=tk.StringVar(value='directx');wrap=tk.BooleanVar(value=False);alpha=tk.BooleanVar(value=False);face=tk.IntVar(value=128)
 ttk.Label(bar,text='Strength').pack(side='left');ttk.Entry(bar,textvariable=strength,width=6).pack(side='left')
 ttk.Combobox(bar,textvariable=convention,values=['directx','opengl'],state='readonly',width=10).pack(side='left')
 ttk.Checkbutton(bar,text='Tile edges',variable=wrap).pack(side='left');ttk.Checkbutton(bar,text='Specular in alpha',variable=alpha).pack(side='left')
 ttk.Label(bar,text='Cube size').pack(side='left');ttk.Combobox(bar,textvariable=face,values=[64,128,256,512],state='readonly',width=5).pack(side='left')
 bar=ttk.Frame(f);bar.pack(fill='x');to=output(f)
 def material():
  from .textures import build_material
  h=filedialog.askopenfilename(title='Select height image')
  if not h:return
  m=filedialog.askopenfilename(title='Select specular mask')
  if not m:return
  parent=filedialog.askdirectory(title='Choose parent for new texture-material directory')
  if not parent:return
  try:
   from pathlib import Path
   show(to,build_material(h,m,Path(parent)/'texture-material',strength.get(),convention.get(),wrap.get(),alpha.get()))
  except (OSError,ValueError,ImportError,tk.TclError) as e:messagebox.showerror('Texture generation failed',str(e))
 def cube():
  from .textures import build_cube
  source=filedialog.askopenfilename(title='Select 2:1 panorama')
  if not source:return
  parent=filedialog.askdirectory(title='Choose parent for new texture-cube directory')
  if not parent:return
  try:
   from pathlib import Path
   show(to,build_cube(source,Path(parent)/'texture-cube',face.get()))
  except (OSError,ValueError,ImportError,tk.TclError) as e:messagebox.showerror('Cubemap generation failed',str(e))
 ttk.Button(bar,text='Generate material maps',command=material).pack(side='left')
 ttk.Button(bar,text='Generate cubemap',command=cube).pack(side='left')
 f=tab('Load order'); ttk.Label(f,text='Scan a JSON load-order profile, without altering installed plugins.').pack(anchor='w')
 bar=ttk.Frame(f);bar.pack(fill='x');lo=output(f)
 def scan_order():
  path=filedialog.askopenfilename(title='Select profile JSON',filetypes=[('JSON','*.json')])
  if not path:return
  try:
   from pathlib import Path
   from .loadorder import HeaderCache,scan_profile
   p=Path(path).resolve();c=json.loads(p.read_text(encoding='utf-8'));cache=HeaderCache(p.parent/'.chimster-header-cache.sqlite')
   try:show(lo,scan_profile(c['game'],[p.parent/d for d in c['data_dirs']],c['plugins'],cache,c.get('after',[])))
   finally:cache.close()
  except (OSError,ValueError,KeyError,TypeError) as e:messagebox.showerror('Profile scan failed',str(e))
 ttk.Button(bar,text='Scan profile',command=scan_order).pack(side='left')
 f=tab('Installed tools'); bar=ttk.Frame(f);bar.pack(fill='x');det=output(f)
 from .tooling import discover_tools
 ttk.Button(bar,text='Detect executables',command=lambda:show(det,discover_tools())).pack(side='left')
 f=tab('3D viewport')
 from .viewport import mount
 mount(f)
 f=tab('Worldspace validator')
 ttk.Label(f,text='Add copied plugins in active load order, masters first. Read-only.').pack(anchor='w')
 pathlist=tk.Listbox(f,height=6);pathlist.pack(fill='x')
 bar=ttk.Frame(f);bar.pack(fill='x');wo=output(f)
 def add_world_plugins():
  for p in filedialog.askopenfilenames(filetypes=[('Plugins','*.esm *.esp')]):
   if p not in pathlist.get(0,'end'):pathlist.insert('end',p)
 def move_world_plugin(delta):
  if not pathlist.curselection():return
  i=pathlist.curselection()[0];j=i+delta
  if 0<=j<pathlist.size():
   value=pathlist.get(i);pathlist.delete(i);pathlist.insert(j,value);pathlist.selection_set(j)
 def check_world():
  from .world_validator import validate
  try:show(wo,validate(pathlist.get(0,'end')))
  except (OSError,ValueError,TypeError) as e:messagebox.showerror('Worldspace validator',str(e))
 ttk.Button(bar,text='Add plugins',command=add_world_plugins).pack(side='left')
 ttk.Button(bar,text='Up',command=lambda:move_world_plugin(-1)).pack(side='left')
 ttk.Button(bar,text='Down',command=lambda:move_world_plugin(1)).pack(side='left')
 ttk.Button(bar,text='Clear',command=lambda:pathlist.delete(0,'end')).pack(side='left')
 ttk.Button(bar,text='Validate',command=check_world).pack(side='left')
 f=tab('Terrain editor')
 from .terrain_ui import mount as mount_terrain
 mount_terrain(f)
 f=tab('Books & notes')
 from .book_ui import mount as mount_books
 mount_books(f)
 f=tab('Dialogue views')
 from .dialogue_view_ui import mount as mount_dialogue_views
 mount_dialogue_views(f)
 f=tab('Quest editor')
 from .quest_ui import mount as mount_quests
 mount_quests(f)
 f=tab('Minigame editor')
 from .minigame_ui import mount as mount_minigames
 mount_minigames(f)
 f=tab('Local wiki')
 ttk.Label(f,text='Bundled documentation — no hosting or internet required.').pack(anchor='w')
 from .wiki import Wiki
 try:
  wiki=Wiki()
  query=tk.StringVar();bar=ttk.Frame(f);bar.pack(fill='x')
  search_entry=ttk.Entry(bar,textvariable=query);search_entry.pack(side='left',fill='x',expand=True)
  pane=ttk.Panedwindow(f,orient='horizontal');pane.pack(fill='both',expand=True,pady=6)
  left=ttk.Frame(pane);right=ttk.Frame(pane);pane.add(left,weight=1);pane.add(right,weight=3)
  pages=tk.Listbox(left,exportselection=False,width=34);pages.pack(side='left',fill='both',expand=True)
  sb=ttk.Scrollbar(left,command=pages.yview);sb.pack(side='right',fill='y');pages.configure(yscrollcommand=sb.set)
  body=tk.Text(right,wrap='word',bg='#1c2229',fg='#d6dce0',state='disabled');body.pack(side='left',fill='both',expand=True)
  sb2=ttk.Scrollbar(right,command=body.yview);sb2.pack(side='right',fill='y');body.configure(yscrollcommand=sb2.set)
  visible=[]
  def display_page(event=None):
   if not pages.curselection():return
   page=wiki.read(visible[pages.curselection()[0]])
   body.configure(state='normal');body.delete('1.0','end');body.insert('1.0',page['body']);body.configure(state='disabled')
  def refresh_wiki():
   titles={p['id']:p['title'] for p in wiki.pages()}
   ids=[r['id'] for r in wiki.search(query.get(),30)] if query.get().strip() else list(titles)
   visible[:]=ids;pages.delete(0,'end')
   for key in ids:pages.insert('end',titles.get(key,key))
   if ids:pages.selection_set(0);display_page()
   else:
    body.configure(state='normal');body.delete('1.0','end');body.insert('1.0','No matching pages.');body.configure(state='disabled')
  ttk.Button(bar,text='Search',command=refresh_wiki).pack(side='left')
  ttk.Button(bar,text='All pages',command=lambda:(query.set(''),refresh_wiki())).pack(side='left')
  search_entry.bind('<Return>',lambda e:refresh_wiki())
  pages.bind('<<ListboxSelect>>',display_page);refresh_wiki()
  def close_app():
   wiki.close();root.destroy()
  root.protocol('WM_DELETE_WINDOW',close_app)
 except (OSError,ValueError,ImportError) as e:
  ttk.Label(f,text='Documentation unavailable: '+str(e)).pack(anchor='w')
 root.mainloop()
