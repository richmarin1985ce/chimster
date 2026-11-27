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
 a=s.add_parser('knowledge'); a.add_argument('index'); a.add_argument('--rebuild'); a.add_argument('--query')
 a=s.add_parser('local-ai'); a.add_argument('model'); a.add_argument('game',choices=PROFILES); a.add_argument('request')
 a=s.add_parser('wiki'); w=a.add_subparsers(dest='wikiop',required=True)
 w.add_parser('list')
 b=w.add_parser('search'); b.add_argument('query')
 b=w.add_parser('read'); b.add_argument('page')
 b=w.add_parser('ask'); b.add_argument('model'); b.add_argument('game',choices=PROFILES); b.add_argument('query')
 a=s.add_parser('modern-nif'); a.add_argument('game',choices=['fallout3','newvegas','skyrim','skyrimse','skyrimvr','fallout4','fallout4vr']); a.add_argument('obj'); a.add_argument('output'); a.add_argument('helper'); a.add_argument('--materials'); a.add_argument('--scale',type=float,default=1)
 collision=a.add_mutually_exclusive_group(); collision.add_argument('--box-collision',action='store_true'); collision.add_argument('--compound-collision',help='Explicit compound box recipe JSON')
 a=s.add_parser('scene-demo'); a.add_argument('output')
 a=s.add_parser('native-flora'); a.add_argument('game',choices=['fallout3','newvegas','skyrim','skyrimse','skyrimvr','fallout4','fallout4vr']); a.add_argument('output'); a.add_argument('helper'); a.add_argument('--seed',type=int,default=42); a.add_argument('--scale',type=float,default=1); a.add_argument('--size',type=int,default=64)
 a=s.add_parser('render-preview'); a.add_argument('output'); a.add_argument('--scene'); a.add_argument('--materials'); a.add_argument('--backend'); a.add_argument('--width',type=int,default=960); a.add_argument('--height',type=int,default=540); a.add_argument('--zoom',type=float,default=12); a.add_argument('--lod',type=float,nargs=3,default=[22,45,90])
 a=s.add_parser('book'); b=a.add_subparsers(dest='bookop',required=True)
 c=b.add_parser('inspect'); c.add_argument('project')
 c=b.add_parser('export'); c.add_argument('project'); c.add_argument('output')
 c=b.add_parser('native'); c.add_argument('project'); c.add_argument('output'); c.add_argument('--model'); c.add_argument('--skill',type=int,default=-1); c.add_argument('--untakeable',action='store_true')
 a=s.add_parser('render-benchmark'); a.add_argument('--count',type=int,default=2500); a.add_argument('--backend',default='egl'); a.add_argument('--frames',type=int,default=5)
 a=s.add_parser('fnv-world'); a.add_argument('heightmap'); a.add_argument('output'); a.add_argument('--spacing-m',type=float,required=True); a.add_argument('--datum-m',type=float); a.add_argument('--origin',type=int,nargs=2,default=[-4,-4]); a.add_argument('--editor-id',default='ChimsterWorld'); a.add_argument('--title',default='Chimster World'); a.add_argument('--vertical-scale',type=float,default=1)
 a.add_argument('--content'); a.add_argument('--ledger-in'); a.add_argument('--ledger-out')
 a=s.add_parser('collision-box'); a.add_argument('obj'); a.add_argument('output'); a.add_argument('--compound',action='store_true')
 a=s.add_parser('minigame'); a.add_argument('project'); a.add_argument('output')
 a=s.add_parser('compatibility'); c=a.add_subparsers(dest='compatop',required=True)
 b=c.add_parser('inspect'); b.add_argument('game',choices=['oblivionremastered','fallout76']); b.add_argument('path')
 b=c.add_parser('snapshot'); b.add_argument('game',choices=['oblivionremastered','fallout76']); b.add_argument('root'); b.add_argument('release')
 b=c.add_parser('compare'); b.add_argument('old'); b.add_argument('new')
 b=c.add_parser('package-layout'); b.add_argument('paths',nargs='+')
 a=s.add_parser('world-check'); a.add_argument('plugins',nargs='+'); a.add_argument('--strict',action='store_true')
 a=s.add_parser('landscape-budget'); a.add_argument('game',choices=['oblivion','fallout3','newvegas']); a.add_argument('plugin')
 a=s.add_parser('record-inspect'); a.add_argument('plugin'); a.add_argument('origin'); a.add_argument('id',type=lambda x:int(x,0))
 a=s.add_parser('record-edit-text'); a.add_argument('plugin'); a.add_argument('output'); a.add_argument('origin'); a.add_argument('id',type=lambda x:int(x,0)); a.add_argument('field'); a.add_argument('value'); a.add_argument('hash')
 a=s.add_parser('record-compare'); a.add_argument('old'); a.add_argument('new')
 a=s.add_parser('building'); a.add_argument('output'); a.add_argument('--width',type=float,default=8); a.add_argument('--depth',type=float,default=6); a.add_argument('--height',type=float,default=3)
 a=s.add_parser('terrain-tile'); a.add_argument('heights'); a.add_argument('output'); a.add_argument('--spacing-m',type=float,required=True); a.add_argument('--x',type=int,default=0); a.add_argument('--y',type=int,default=0); a.add_argument('--step',type=int,default=4)
 a=s.add_parser('chunk-build'); a.add_argument('placements'); a.add_argument('output'); a.add_argument('--size',type=float,default=128)
 a=s.add_parser('chunk-load'); a.add_argument('folder'); a.add_argument('x',type=float); a.add_argument('y',type=float); a.add_argument('--radius',type=int,default=1)
 a=s.add_parser('quest-check'); a.add_argument('project')
 a=s.add_parser('script-check'); a.add_argument('path')
 a=s.add_parser('quest-states'); a.add_argument('project'); a.add_argument('--max-states',type=int,default=100000)
 a=s.add_parser('quest-native'); a.add_argument('project'); a.add_argument('output'); a.add_argument('--master',action='append',default=[]); a.add_argument('--ledger-in'); a.add_argument('--ledger-out'); a.add_argument('--script-draft',action='store_true')
 a=s.add_parser('quest-attach-scripts'); a.add_argument('draft'); a.add_argument('compiled'); a.add_argument('output')
 a=s.add_parser('quest-scenes'); a.add_argument('project'); a.add_argument('--scene')
 a=s.add_parser('dialogue-view-inspect'); a.add_argument('xml')
 a=s.add_parser('dialogue-view-remap'); a.add_argument('source'); a.add_argument('output'); a.add_argument('mapping'); a.add_argument('--positions')
 a=s.add_parser('quest-scripts'); a.add_argument('project'); a.add_argument('output')
 a=s.add_parser('interior-check'); a.add_argument('project'); a.add_argument('--room'); a.add_argument('--closed',action='append',default=[])
 a=s.add_parser('record-edit'); a.add_argument('plugin'); a.add_argument('output'); a.add_argument('origin'); a.add_argument('id',type=lambda x:int(x,0)); a.add_argument('field'); a.add_argument('value_json'); a.add_argument('hash')
 a=s.add_parser('record-build'); a.add_argument('project'); a.add_argument('output'); a.add_argument('--master',action='append',default=[]); a.add_argument('--ledger-in'); a.add_argument('--ledger-out')
 a=s.add_parser('master-reorder'); a.add_argument('source'); a.add_argument('output'); a.add_argument('masters',nargs='+')
 a=s.add_parser('project'); c=a.add_subparsers(dest='project_op',required=True)
 b=c.add_parser('create'); b.add_argument('root'); b.add_argument('name'); b.add_argument('game',choices=PROFILES)
 for name in ('status','verify'):
  b=c.add_parser(name); b.add_argument('root')
 b=c.add_parser('add'); b.add_argument('root'); b.add_argument('id'); b.add_argument('kind'); b.add_argument('source'); b.add_argument('--revision',type=int,required=True); b.add_argument('--replace',action='store_true')
 b=c.add_parser('batch'); b.add_argument('root'); b.add_argument('changes'); b.add_argument('--revision',type=int,required=True)
 b=c.add_parser('remove'); b.add_argument('root'); b.add_argument('id'); b.add_argument('--revision',type=int,required=True)
 b=c.add_parser('export'); b.add_argument('root'); b.add_argument('id'); b.add_argument('output')
 b=c.add_parser('rollback'); b.add_argument('root'); b.add_argument('target',type=int); b.add_argument('--revision',type=int,required=True)
 b=c.add_parser('build'); b.add_argument('root'); b.add_argument('kind',choices=['records','quest']); b.add_argument('source'); b.add_argument('id'); b.add_argument('filename'); b.add_argument('--revision',type=int,required=True); b.add_argument('--master',action='append',default=[]); b.add_argument('--script-draft',action='store_true')
 a=s.add_parser('dependencies'); c=a.add_subparsers(dest='dependency_op',required=True)
 b=c.add_parser('status'); b.add_argument('--config')
 b=c.add_parser('pin'); b.add_argument('config'); b.add_argument('tool'); b.add_argument('executable')
 a=s.add_parser('extension-approve'); a.add_argument('manifest'); a.add_argument('executable'); a.add_argument('trust')
 a=s.add_parser('extension-run'); a.add_argument('trust'); a.add_argument('capability'); a.add_argument('payload'); a.add_argument('--execute',action='store_true')
 a=s.add_parser('app-release'); c=a.add_subparsers(dest='release_op',required=True)
 b=c.add_parser('build'); b.add_argument('source'); b.add_argument('output'); b.add_argument('version'); b.add_argument('entrypoint')
 b=c.add_parser('verify'); b.add_argument('archive'); b.add_argument('--sha256')
 b=c.add_parser('install'); b.add_argument('root'); b.add_argument('archive'); b.add_argument('--sha256',required=True); b.add_argument('--activate',action='store_true')
 b=c.add_parser('activate'); b.add_argument('root'); b.add_argument('version')
 b=c.add_parser('status'); b.add_argument('root')
 a=s.add_parser('wiki-export'); a.add_argument('output')
 a=s.add_parser('wiki-audit')
 a=s.add_parser('localization-project'); c=a.add_subparsers(dest='loc_op',required=True)
 b=c.add_parser('catalog'); b.add_argument('kind',choices=['book','quest','strings']); b.add_argument('source'); b.add_argument('output')
 b=c.add_parser('suggest'); b.add_argument('catalog'); b.add_argument('database'); b.add_argument('src'); b.add_argument('dst'); b.add_argument('output')
 b=c.add_parser('review'); b.add_argument('catalog'); b.add_argument('--encoding',default='utf-8')
 b=c.add_parser('remember'); b.add_argument('catalog'); b.add_argument('database')
 b=c.add_parser('apply'); b.add_argument('catalog'); b.add_argument('source'); b.add_argument('output'); b.add_argument('--encoding',default='utf-8')
 b=c.add_parser('pack'); b.add_argument('source'); b.add_argument('output'); b.add_argument('kind',choices=['STRINGS','DLSTRINGS','ILSTRINGS']); b.add_argument('--encoding',required=True)
 n=p.parse_args()
 try:
  if n.cmd=='ui':
   from .ui import launch
   launch(); return
  if n.cmd in ('wiki-export','wiki-audit'):
   from .wiki import Wiki
   from .wiki_render import export,audit
   with Wiki() as wiki:result=export(wiki,n.output) if n.cmd=='wiki-export' else audit(wiki)
  elif n.cmd=='localization-project':
   from . import localization_project as loc
   from .project import read_json
   from pathlib import Path
   op=n.loc_op
   if op=='catalog':
    data=loc.catalog(n.kind,n.source);loc.save_json(data,n.output);result={'output':n.output,'entries':len(data['entries'])}
   elif op=='pack':result=loc.pack_native(n.source,n.output,n.kind,n.encoding)
   else:
    data=read_json(Path(n.catalog))
    if op=='suggest':
     data=loc.suggest(data,n.database,n.src,n.dst);loc.save_json(data,n.output);result={'output':n.output,'suggested':sum(r['status']=='suggested' for r in data['entries'])}
    elif op=='review':
     result=loc.review(data,n.encoding)
     print(json.dumps(result,indent=2))
     if not result['valid']:raise SystemExit(1)
     return
    elif op=='remember':result=loc.remember(data,n.database)
    else:result=loc.apply(data,n.source,n.output,n.encoding)
  elif n.cmd=='project':
   from .project import Project,read_json
   from pathlib import Path
   if n.project_op=='create':result=Project.create(n.root,n.name,n.game).read()
   else:
    project=Project(n.root)
    if n.project_op=='status':result=project.read()
    elif n.project_op=='verify':result=project.verify()
    elif n.project_op=='add':result=project.add(n.id,n.kind,n.source,n.revision,n.replace)
    elif n.project_op=='batch':result=project.batch(read_json(Path(n.changes)),n.revision)
    elif n.project_op=='remove':result=project.remove(n.id,n.revision)
    elif n.project_op=='export':result={'output':project.export(n.id,n.output)}
    elif n.project_op=='rollback':result=project.rollback(n.target,n.revision)
    else:
     from .project_build import build
     result=build(project,n.kind,n.source,n.id,n.filename,n.revision,n.master,n.script_draft)
  elif n.cmd=='dependencies':
   from .dependencies import pin,report
   result=report(n.config) if n.dependency_op=='status' else pin(n.config,n.tool,n.executable)
  elif n.cmd=='extension-approve':
   from .extension_runtime import approve
   result=approve(n.manifest,n.executable,n.trust)
  elif n.cmd=='extension-run':
   from .extension_runtime import invoke
   from .project import read_json
   from pathlib import Path
   result=invoke(n.trust,n.capability,read_json(Path(n.payload)),execute=n.execute)
  elif n.cmd=='app-release':
   from .app_releases import build,verify_archive,Installation
   if n.release_op=='build':result=build(n.source,n.output,n.version,n.entrypoint)
   elif n.release_op=='verify':result=verify_archive(n.archive,n.sha256)
   else:
    inst=Installation(n.root)
    if n.release_op=='install':result=inst.install(n.archive,n.sha256,n.activate)
    elif n.release_op=='activate':result=inst.activate(n.version)
    else:result=inst.status()
  elif n.cmd=='quest-states':
   from .quest_editor import load
   from .quest_states import analyze
   result=analyze(load(n.project),n.max_states)
   print(json.dumps(result,indent=2))
   if not result['valid']:raise SystemExit(1)
   return
  elif n.cmd=='quest-native':
   from .quest_editor import load
   from .fnv_quest import export
   from .formids import staged_build
   spec=load(n.project)
   if n.ledger_in and not n.ledger_out:raise ValueError('previous ledger requires output ledger')
   result=staged_build(lambda ids:export(spec,n.output,n.master,ids,script_draft=n.script_draft),n.output,n.ledger_out,n.ledger_in) if n.ledger_out else export(spec,n.output,n.master,script_draft=n.script_draft)
  elif n.cmd=='quest-attach-scripts':
   from .quest_compile import attach
   result=attach(n.draft,n.compiled,n.output)
  elif n.cmd=='quest-scenes':
   from .quest_editor import load
   from .quest_scenes import validate,timeline
   spec=load(n.project);result=timeline(spec,n.scene) if n.scene else validate(spec)
  elif n.cmd=='dialogue-view-inspect':
   from .dialogue_views import parse,inspect
   result=inspect(parse(n.xml))
  elif n.cmd=='dialogue-view-remap':
   from .quest_editor import load
   from .dialogue_views import remap
   result=remap(n.source,n.output,load(n.mapping),positions=load(n.positions) if n.positions else None)
  elif n.cmd=='quest-scripts':
   from .quest_editor import load
   from .quest_scripts import export
   result=export(load(n.project),n.output)
  elif n.cmd=='interior-check':
   from .quest_editor import load
   from .interior_layout import validate,candidates
   layout=load(n.project);result=validate(layout)
   if n.room and result['valid']:result['visibility']=candidates(layout,n.room,n.closed)
   print(json.dumps(result,indent=2))
   if not result['valid']:raise SystemExit(1)
   return
  elif n.cmd=='script-check':
   from .script_lint import check_file
   result=check_file(n.path)
   print(json.dumps(result,indent=2))
   if not result['valid']:raise SystemExit(1)
   return
  elif n.cmd=='landscape-budget':
   from .texture_budget import scan_land
   result=scan_land(n.plugin,n.game)
   print(json.dumps(result,indent=2))
   if not result['valid']:raise SystemExit(1)
   return
  elif n.cmd=='record-inspect':
   from .record_editor import inspect
   result=inspect(n.plugin,n.origin,n.id)
  elif n.cmd=='record-edit':
   from .record_editor import edit_typed
   result=edit_typed(n.plugin,n.output,n.origin,n.id,n.field,json.loads(n.value_json),n.hash)
  elif n.cmd=='record-build':
   from .record_project import export
   from .quest_editor import load
   from .formids import staged_build
   spec=load(n.project)
   if n.ledger_in and not n.ledger_out:raise ValueError('previous ledger requires output ledger')
   result=staged_build(lambda ids:export(spec,n.output,n.master,ids),n.output,n.ledger_out,n.ledger_in) if n.ledger_out else export(spec,n.output,n.master)
  elif n.cmd=='master-reorder':
   from .master_remap import reorder
   result=reorder(n.source,n.output,n.masters)
  elif n.cmd=='record-edit-text':
   from .record_editor import edit_text
   result=edit_text(n.plugin,n.output,n.origin,n.id,n.field,n.value,n.hash)
  elif n.cmd=='record-compare':
   from .plugin_compare import compare
   result=compare(n.old,n.new)
  elif n.cmd=='building':
   from .architecture import Building,export
   result=export(Building(width=n.width,depth=n.depth,height=n.height),n.output)
  elif n.cmd=='terrain-tile':
   from .worldspace import Terrain
   from .terrain_tiles import tile
   from .flora import write_obj
   m=tile(Terrain.load(n.heights,n.spacing_m),n.x,n.y,n.step)
   write_obj(m,n.output);result=m.stats()
  elif n.cmd=='chunk-build':
   from .world_chunks import build
   from pathlib import Path
   result=build(json.loads(Path(n.placements).read_text(encoding='utf-8')),n.output,n.size)
  elif n.cmd=='chunk-load':
   from .world_chunks import load
   result=load(n.folder,n.x,n.y,n.radius)
  elif n.cmd=='quest-check':
   from .quest_editor import load,validate
   result=validate(load(n.project))
   print(json.dumps(result,indent=2))
   if not result['valid']:raise SystemExit(1)
   return
  elif n.cmd=='world-check':
   from .world_validator import validate
   result=validate(n.plugins)
   print(json.dumps(result,indent=2))
   if not result['valid'] or (n.strict and result['warnings']):raise SystemExit(1)
   return
  elif n.cmd=='minigame':
   from .minigames import load,export
   result=export(load(n.project),n.output)
  elif n.cmd=='compatibility':
   from . import compatibility as c
   from pathlib import Path
   if n.compatop=='inspect':result=c.inspect(n.path,n.game)
   elif n.compatop=='snapshot':result=c.snapshot(n.root,n.game,n.release)
   elif n.compatop=='compare':result=c.compare(json.loads(Path(n.old).read_text(encoding='utf-8')),json.loads(Path(n.new).read_text(encoding='utf-8')))
   else:result=c.remaster_package(n.paths)
  elif n.cmd=='fnv-world':
   from .worldspace import Terrain
   from .fnv_world import build
   terrain=Terrain.load(n.heightmap,n.spacing_m,n.datum_m)
   from pathlib import Path
   content=json.loads(Path(n.content).read_text(encoding='utf-8')) if n.content else None
   from .formids import staged_build
   if n.ledger_in and not n.ledger_out:raise ValueError('previous ledger requires output ledger')
   args=(terrain,n.output,n.editor_id,n.title,tuple(n.origin),n.vertical_scale,content)
   result=staged_build(lambda ids:build(*args,allocator=ids),n.output,n.ledger_out,n.ledger_in) if n.ledger_out else build(*args)
  elif n.cmd=='collision-box':
   from .collision import export_box,export_compound
   from .scene import load_obj
   result=(export_compound if n.compound else export_box)(load_obj(n.obj),n.output)
  elif n.cmd=='book':
   from .books import load,export
   book=load(n.project)
   if n.bookop=='export':result=export(book,n.output)
   elif n.bookop=='native':
    from .fnv_content import export_book
    result=export_book(book,n.output,n.model,n.skill,n.untakeable)
   else:result={'editor_id':book.editor_id,'title':book.title,'pages':len(book.pages),'game':book.game,'kind':book.kind,'strings':book.localization()}
  elif n.cmd=='render-benchmark':
   from .render_benchmark import benchmark
   result=benchmark(n.count,n.frames,n.backend)
  elif n.cmd=='render-preview':
   from .gpu_viewport import Renderer,Settings,make_demo,load_materials
   from .scene import Scene,Camera
   from .atlas import write_png
   if n.scene:scene,materials=Scene.load(n.scene),{}
   else:scene,materials=make_demo()
   if n.materials:materials=load_materials(n.materials)
   renderer=Renderer(n.backend)
   try:
    raw,result=renderer.render(scene,Camera(zoom=n.zoom),n.width,n.height,materials,Settings(lod_distances=tuple(n.lod)))
    write_png(n.output,n.width,n.height,raw)
   finally:renderer.close()
  elif n.cmd=='native-flora':
   from .native_flora import build_native_flora
   from .flora import Recipe
   result=build_native_flora(Recipe(seed=n.seed),n.game,n.output,n.helper,n.scale,n.size)
  elif n.cmd=='modern-nif':
   from .modern_nif import export
   from .scene import load_obj
   from pathlib import Path
   mats=json.loads(Path(n.materials).read_text(encoding='utf-8')) if n.materials else None
   from .collision_materials import load as load_collision
   compound=load_collision(n.compound_collision) if n.compound_collision else None
   result=export(load_obj(n.obj),n.game,n.output,n.helper,mats,n.scale,n.box_collision,compound)
  elif n.cmd=='scene-demo':
   from .scene import demo_scene
   scene=demo_scene();scene.save(n.output);result={'output':n.output,'instances':len(scene.instances)}
  elif n.cmd=='wiki':
   from .wiki import Wiki
   with Wiki() as wiki:
    if n.wikiop=='list':result=wiki.pages()
    elif n.wikiop=='search':result=wiki.search(n.query)
    elif n.wikiop=='read':result=wiki.read(n.page)
    else:
     from .local_ai import propose
     refs=wiki.context(n.query)
     result=propose(n.model,n.game,n.query,references=refs)
     result['retrieved_references']=refs
  elif n.cmd=='knowledge':
   from .knowledge import KnowledgeIndex
   idx=KnowledgeIndex(n.index)
   try:
    result={}
    if n.rebuild:result.update(idx.rebuild(n.rebuild))
    if n.query:result['matches']=idx.search(n.query)
   finally:idx.close()
  elif n.cmd=='local-ai':
   from .local_ai import propose
   result=propose(n.model,n.game,n.request)
  elif n.cmd=='textures':
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
