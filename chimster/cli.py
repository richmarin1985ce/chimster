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
 n=p.parse_args()
 try:
  if n.cmd=='ui':
   from .ui import launch
   launch(); return
  if n.cmd=='asset-plan':
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
 except (OSError,ValueError) as e: p.exit(2,f'Error: {e}\n')
if __name__=='__main__': main()
