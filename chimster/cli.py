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
 n=p.parse_args()
 try:
  if n.cmd=='ui':
   from .ui import launch
   launch(); return
  if n.cmd=='openmw':
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
