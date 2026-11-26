import argparse,json
from .core import catalog, inspect_plugin, plan, PROFILES

def main():
 p=argparse.ArgumentParser(prog='chimster'); s=p.add_subparsers(dest='cmd',required=True)
 a=s.add_parser('tools'); a.add_argument('--game',choices=PROFILES)
 a=s.add_parser('inspect'); a.add_argument('game',choices=PROFILES); a.add_argument('path')
 a=s.add_parser('plan'); a.add_argument('game',choices=PROFILES); a.add_argument('request')
 a=s.add_parser('ui')
 a=s.add_parser('openmw'); o=a.add_subparsers(dest='operation',required=True)
 o.add_parser('discover')
 b=o.add_parser('preview'); b.add_argument('profile')
 b=o.add_parser('launch'); b.add_argument('profile'); b.add_argument('--executable')
 b=o.add_parser('editor'); b.add_argument('--executable')
 b=o.add_parser('reload-plan'); b.add_argument('paths',nargs='+')
 a=s.add_parser('flora'); a.add_argument('output'); a.add_argument('--species',choices=['tree','shrub','grass'],default='tree'); a.add_argument('--seed',type=int,default=42); a.add_argument('--count',type=int,default=1); a.add_argument('--height',type=float,default=8.0); a.add_argument('--branches',type=int,default=24); a.add_argument('--leaves',type=int,default=240)
 a=s.add_parser('xedit'); x=a.add_subparsers(dest='xoperation',required=True)
 b=x.add_parser('discover'); b.add_argument('game')
 for name in ('preview','launch'):
  b=x.add_parser(name); b.add_argument('profile'); b.add_argument('executable'); b.add_argument('--operation',choices=['inspect','conflicts','lod'],default='inspect')
 b=x.add_parser('report'); b.add_argument('logfile')
 a=s.add_parser('asset-plan'); a.add_argument('game'); a.add_argument('data'); a.add_argument('manifest')
 a=s.add_parser('loadorder'); a.add_argument('profile'); a.add_argument('--cache',required=True)
 a=s.add_parser('autopatch'); a.add_argument('snapshot')
 a=s.add_parser('discover-tools')
 a=s.add_parser('extension-info'); a.add_argument('manifest')
 a=s.add_parser('install-zip'); a.add_argument('root'); a.add_argument('archive'); a.add_argument('mod_id')
 a=s.add_parser('save-profile'); a.add_argument('root'); a.add_argument('name'); a.add_argument('config')
 a=s.add_parser('tes3-inventory'); a.add_argument('path')
 a=s.add_parser('tes3-static-override'); a.add_argument('base'); a.add_argument('output'); a.add_argument('editor_id'); a.add_argument('model')
 a=s.add_parser('audit-assets'); a.add_argument('config')
 a=s.add_parser('fomod'); a.add_argument('root'); a.add_argument('config')
 a=s.add_parser('ffdec'); a.add_argument('mode',choices=['export','import']); a.add_argument('executable'); a.add_argument('source'); a.add_argument('output'); a.add_argument('--scripts'); a.add_argument('--execute',action='store_true')
 a=s.add_parser('git-history'); a.add_argument('root'); a.add_argument('path')
 a=s.add_parser('git-branches'); a.add_argument('root'); a.add_argument('--create')
 a=s.add_parser('lod'); l=a.add_subparsers(dest='lop',required=True)
 b=l.add_parser('tree'); b.add_argument('output'); b.add_argument('--seed',type=int,default=42); b.add_argument('--size',type=int,default=128); b.add_argument('--views',type=int,choices=[1,2,4],default=2)
 b=l.add_parser('nif'); b.add_argument('output'); b.add_argument('--seed',type=int,default=42); b.add_argument('--level',type=int,choices=[0,1,2],default=2); b.add_argument('--scale',type=float,default=1)
 b=l.add_parser('legacy-billboard'); b.add_argument('output'); b.add_argument('--seed',type=int,default=42); b.add_argument('--size',type=int,default=128); b.add_argument('--views',type=int,choices=[1,2,4],default=2); b.add_argument('--scale',type=float,default=1)
 b=l.add_parser('terrain'); b.add_argument('heightmap'); b.add_argument('output'); b.add_argument('--step',type=int,default=2)
 b=l.add_parser('benchmark'); b.add_argument('--count',type=int,default=10); b.add_argument('--size',type=int,default=64)
 b=l.add_parser('compare-traces'); b.add_argument('baseline'); b.add_argument('changed')
 b=l.add_parser('workflow'); b.add_argument('game')
 b=l.add_parser('tool'); b.add_argument('profile'); b.add_argument('tool',choices=['xlodgen','texgen','dyndolod']); b.add_argument('executable'); b.add_argument('--execute',action='store_true')
 b=l.add_parser('openmw-settings'); b.add_argument('--distance',type=float,default=32768); b.add_argument('--min-size',type=float,default=.023)
 b=l.add_parser('mge'); b.add_argument('game_copy')
 a=s.add_parser('localization-audit'); a.add_argument('source'); a.add_argument('target')
 a=s.add_parser('flagstaff'); f=a.add_subparsers(dest='fop',required=True)
 b=f.add_parser('fetch'); b.add_argument('recipe'); b.add_argument('dem')
 b=f.add_parser('build'); b.add_argument('recipe'); b.add_argument('dem'); b.add_argument('output')
 a=s.add_parser('fnv-index'); a.add_argument('cache'); a.add_argument('plugins',nargs='+'); a.add_argument('--origin'); a.add_argument('--id',type=lambda x:int(x,0))
 a=s.add_parser('fnv-gmst-patch'); a.add_argument('output'); a.add_argument('origin'); a.add_argument('--id',action='append',type=lambda x:int(x,0),required=True); a.add_argument('plugins',nargs='+')
 a=s.add_parser('textures'); t=a.add_subparsers(dest='texop',required=True)
 b=t.add_parser('material'); b.add_argument('height'); b.add_argument('mask'); b.add_argument('output'); b.add_argument('--strength',type=float,default=4); b.add_argument('--convention',choices=['directx','opengl'],default='directx'); b.add_argument('--wrap',action='store_true'); b.add_argument('--pack-alpha',action='store_true'); b.add_argument('--low',type=float,default=.04); b.add_argument('--high',type=float,default=.5)
 b=t.add_parser('cube'); b.add_argument('panorama'); b.add_argument('output'); b.add_argument('--size',type=int,default=128)
 a=s.add_parser('stage-overlay'); a.add_argument('output'); a.add_argument('sources',nargs='+')
 a=s.add_parser('external-tool'); a.add_argument('tool',choices=['texconv','caprica','champollion','spriggit','bsarch']); a.add_argument('config'); a.add_argument('--execute',action='store_true')
 n=p.parse_args()
 try:
  if n.cmd=='ui':
   from .ui import launch
   launch(); return
  if n.cmd=='textures':
   from .textures import build_material,build_cube
   if n.texop=='material': result=build_material(n.height,n.mask,n.output,n.strength,n.convention,n.wrap,n.pack_alpha,n.low,n.high)
   else:result=build_cube(n.panorama,n.output,n.size)
  elif n.cmd=='stage-overlay':
   from .deploy import stage_overlay
   result=stage_overlay(n.sources,n.output)
  elif n.cmd=='external-tool':
   from pathlib import Path
   from . import integrations
   config=json.loads(Path(n.config).read_text(encoding='utf-8'))
   result=getattr(integrations,n.tool)(**config)
   if n.execute:result=integrations.run(result)
  elif n.cmd=='fnv-index':
   from .fnv_records import RecordIndex
   idx=RecordIndex(n.cache)
   try:
    result=idx.refresh(n.plugins)
    if n.origin is not None and n.id is not None:result['chain']=idx.chain(n.origin,n.id)
   finally:idx.close()
  elif n.cmd=='fnv-gmst-patch':
   from .fnv_patch import build_gmst_patch
   result=build_gmst_patch(n.plugins,n.output,n.origin,n.id)
  elif n.cmd=='flagstaff':
   from .flagstaff import load_recipe,fetch_dem,read_dem,build
   recipe=load_recipe(n.recipe)
   if n.fop=='fetch':result=fetch_dem(recipe,n.dem)
   else:
    grid,metadata=read_dem(recipe,n.dem);result=build(recipe,grid,metadata,n.output)
  elif n.cmd=='localization-audit':
   from pathlib import Path
   from .localization_audit import audit_tables
   result=audit_tables(json.loads(Path(n.source).read_text(encoding='utf-8')),json.loads(Path(n.target).read_text(encoding='utf-8')))
  elif n.cmd=='lod':
   from .lod import build_tree,terrain_grid,benchmark
   from .flora import Recipe,generate,write_obj
   from .lod_tools import tool_plan,run_tool,workflow,openmw_settings,mge_plan
   from pathlib import Path
   if n.lop=='tree':result=build_tree(Recipe(seed=n.seed),n.output,n.size,n.views)
   elif n.lop=='nif':
    from .nif_export import export_legacy
    result=export_legacy(generate(Recipe(seed=n.seed),n.level),n.output,scale=n.scale)
   elif n.lop=='legacy-billboard':
    from .nif_export import export_billboard
    result=export_billboard(Recipe(seed=n.seed),n.output,n.size,n.views,n.scale)
   elif n.lop=='terrain':
    mesh=terrain_grid(json.loads(Path(n.heightmap).read_text(encoding='utf-8')),n.step)
    write_obj(mesh,n.output);result=mesh.stats()
   elif n.lop=='benchmark':result=benchmark(n.count,n.size)
   elif n.lop=='compare-traces':
    from .lod_benchmark import compare
    result=compare(n.baseline,n.changed)
   elif n.lop=='workflow':result=workflow(n.game)
   elif n.lop=='openmw-settings':result={'settings':openmw_settings(n.distance,n.min_size)}
   elif n.lop=='mge':result=mge_plan(n.game_copy)
   else:
    from .xedit import Workspace
    ws=Workspace.load(n.profile);result=tool_plan(ws,n.tool,n.executable)
    if n.execute:result['pid']=run_tool(ws,n.tool,n.executable).pid
  elif n.cmd=='discover-tools':
   from .tooling import discover_tools
   result=discover_tools()
  elif n.cmd=='extension-info':
   from .sdk import load_manifest
   result=load_manifest(n.manifest)
  elif n.cmd=='install-zip':
   from .modprofiles import install_zip
   result={'installed':str(install_zip(n.root,n.archive,n.mod_id)),'activated':False}
  elif n.cmd=='save-profile':
   from .modprofiles import save_profile
   from pathlib import Path
   config=json.loads(Path(n.config).read_text(encoding='utf-8'))
   result={'profile':str(save_profile(n.root,n.name,config['game'],config['mods'],config['plugins']))}
  elif n.cmd=='tes3-inventory':
   from .tes3 import inventory
   result=inventory(n.path)
  elif n.cmd=='tes3-static-override':
   from .tes3 import write_static_override
   result=write_static_override(n.base,n.output,n.editor_id,n.model)
  elif n.cmd=='audit-assets':
   from .validation import index_assets,audit_assets
   from pathlib import Path
   pth=Path(n.config).resolve()
   config=json.loads(pth.read_text(encoding='utf-8'))
   result=audit_assets(index_assets([pth.parent/d for d in config['data_dirs']]),config['references'])
  elif n.cmd=='fomod':
   from .fomod import write_fomod
   from pathlib import Path
   c=json.loads(Path(n.config).read_text(encoding='utf-8'))
   result={'folder':str(write_fomod(n.root,c['name'],c['author'],c['version'],c['files']))}
  elif n.cmd=='ffdec':
   from .ffdec import export_plan,import_plan,execute
   if n.mode=='import' and not n.scripts: raise ValueError('--scripts required')
   args=export_plan(n.executable,n.source,n.output) if n.mode=='export' else import_plan(n.executable,n.source,n.output,n.scripts)
   result={'args':args,'executed':False}
   if n.execute:
    completed=execute(args);result.update(executed=True,stdout=completed.stdout)
  elif n.cmd=='git-history':
   from pathlib import Path
   from .versioning import history
   result=history(Path(n.root),n.path)
  elif n.cmd=='git-branches':
   from pathlib import Path
   from .versioning import branches,create_branch
   if n.create:create_branch(Path(n.root),n.create)
   result=branches(Path(n.root))
  elif n.cmd=='loadorder':
   from pathlib import Path
   from .loadorder import HeaderCache, scan_profile
   profile=Path(n.profile).resolve(strict=True)
   config=json.loads(profile.read_text(encoding='utf-8'))
   cache=HeaderCache(n.cache)
   try:
    result=scan_profile(config['game'],[profile.parent/d for d in config['data_dirs']],config['plugins'],cache,config.get('after',[]))
   finally: cache.close()
  elif n.cmd=='autopatch':
   from pathlib import Path
   from .autopatch import plan
   config=json.loads(Path(n.snapshot).read_text(encoding='utf-8'))
   result=plan(config['plugins'],config['records'],backend_version=config['backend_version'],complete_snapshot=config.get('complete_snapshot') is True)
  elif n.cmd=='asset-plan':
   from .asset_plan import static_proposal
   from pathlib import Path
   result=static_proposal(n.game,n.data,json.loads(Path(n.manifest).read_text(encoding='utf-8')))
  elif n.cmd=='xedit':
   from .xedit import Workspace, discover, preview, launch, report_from_log
   from pathlib import Path
   if n.xoperation=='discover': result=discover(n.game)
   elif n.xoperation=='report': result=report_from_log(Path(n.logfile).read_text(encoding='utf-8-sig'))
   elif n.xoperation=='preview': result=preview(Workspace.load(n.profile),n.executable,n.operation)
   else: result={'pid':launch(Workspace.load(n.profile),n.executable,n.operation).pid}
  elif n.cmd=='flora':
   from .flora import Recipe, batch
   if not 1<=n.count<=1000: raise ValueError('count must be 1..1000')
   result=batch([Recipe(species=n.species,seed=n.seed+i,height=n.height,radius=n.height*.0275,branches=n.branches,leaves=n.leaves) for i in range(n.count)],n.output)
  elif n.cmd=='openmw':
   from .openmw import discover, Profile, launch_game, launch_editor, reload_plan
   if n.operation=='discover': result=discover()
   elif n.operation=='preview': result=Profile.load(n.profile).engine_args()
   elif n.operation=='launch': result={'pid':launch_game(Profile.load(n.profile),n.executable).pid}
   elif n.operation=='editor': result={'pid':launch_editor(n.executable).pid,'warning':'Uses the installed editor profile'}
   else: result=reload_plan(n.paths)
  elif n.cmd=='tools': result=[t for t in catalog() if not n.game or '*' in t['games'] or n.game in t['games']]
  elif n.cmd=='inspect': result=inspect_plugin(n.path,n.game)
  else: result=plan(n.game,n.request)
  print(json.dumps(result,indent=2))
 except (OSError,ValueError,KeyError,TypeError,ImportError,RuntimeError) as e: p.exit(2,f'Error: {e}\n')
if __name__=='__main__': main()
