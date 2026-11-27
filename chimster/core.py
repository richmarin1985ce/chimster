"""Read-only bounded Bethesda plugin scanner and deterministic planning."""
import json, struct
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
PROFILES = {
 'morrowind': ('TES3', 16), 'openmw': ('TES3', 16), 'oblivion': ('TES4', 20),
 'fallout3': ('TES4', 24), 'newvegas': ('TES4', 24), 'skyrim': ('TES4', 24),
 'skyrimse': ('TES4', 24), 'skyrimvr': ('TES4', 24), 'fallout4': ('TES4', 24),
 'fallout4vr': ('TES4', 24), 'starfield': ('TES4', 24), 'oblivionremastered': ('TES4', 24),
}

def catalog():
 return json.loads((ROOT/'tools.json').read_text(encoding='utf-8'))

def inspect_plugin(path, game, limit=1000000):
 if game not in PROFILES: raise ValueError('Unknown game profile')
 path=Path(path); magic, hs=PROFILES[game]; counts=Counter(); masters=[]; flags=0; groups=0; seen=0
 with path.open('rb') as f:
  end=path.stat().st_size
  def read(n):
   b=f.read(n)
   if len(b)!=n: raise ValueError('Truncated file')
   return b
  def scan(bound, depth=0):
   nonlocal flags, groups, seen
   if depth>64: raise ValueError('Group nesting limit exceeded')
   while f.tell()<bound:
    start=f.tell(); seen+=1
    if seen>limit: raise ValueError('Record limit exceeded')
    if bound-start<hs: raise ValueError('Incomplete header')
    h=read(hs); sig=h[:4].decode('ascii',errors='replace'); size=struct.unpack_from('<I',h,4)[0]
    if not all(32<=b<=126 for b in h[:4]): raise ValueError('Invalid record signature')
    if start!=0 and sig==magic: raise ValueError('Unexpected second plugin header')
    if start==0 and sig!=magic: raise ValueError(f'Expected {magic}, got {sig}')
    if sig=='GRUP' and magic=='TES4':
     stop=start+size
     if size<hs or stop>bound: raise ValueError('Invalid group size')
     groups+=1; scan(stop,depth+1); continue
    stop=f.tell()+size
    if stop>bound: raise ValueError(f'Record {sig} exceeds containing file/group')
    counts[sig]+=1
    if start==0:
     flags=struct.unpack_from('<I',h,12 if magic=='TES3' else 8)[0]
     if size>16*1024*1024: raise ValueError('Header too large')
     data=read(size); pos=0; sh=8 if magic=='TES3' else 6; extended=None
     while pos<len(data):
      if len(data)-pos<sh: raise ValueError('Truncated header subrecord')
      sub=data[pos:pos+4]; n=int.from_bytes(data[pos+4:pos+sh],'little'); pos+=sh
      if extended is not None:
       if sub==b'XXXX': raise ValueError('Consecutive XXXX markers')
       n,extended=extended,None
      if pos+n>len(data): raise ValueError('Invalid subrecord length')
      if sub==b'XXXX' and magic=='TES4':
       if n!=4: raise ValueError('Invalid XXXX')
       extended=int.from_bytes(data[pos:pos+n],'little')
      if sub==b'MAST': masters.append(data[pos:pos+n].rstrip(b'\0').decode('utf-8',errors='replace'))
      pos+=n
     if extended is not None: raise ValueError('Dangling XXXX marker')
    else: f.seek(stop)
   if f.tell()!=bound: raise ValueError('Group boundary mismatch')
  if end<hs: raise ValueError('File too short')
  scan(end)
 return {'file':path.name,'game':game,'format':magic,'bytes':end,'header_flags':flags,'masters':masters,'record_counts':dict(sorted(counts.items())),'groups':groups,'mode':'read-only structural inspection; not full format validation'}

RULES = [
 ('terrain', ('terrain','heightmap','landscape','worldspace','town','road'), ['inspect masters and existing cells','import heightmap to an isolated staging area','review placement and texture rules','generate game-specific terrain and LOD','validate seams and test in game']),
 ('quests', ('quest','dialogue','npc','town'), ['index existing NPCs and quest records','draft dialogue and conditions','review dependencies and state transitions','compile game-specific scripts','test quest branches in game']),
 ('assets', ('mesh','texture','asset','model','archive'), ['inventory asset paths and permissions','prepare target-format conversion','validate materials and references','package staged assets']),
 ('conflicts', ('conflict','patch','load order','clean'), ['inspect plugin headers and masters','analyze override winners with game-specific backend','review intentional overrides','create separate patch and test']),
]
def plan(game, request):
 if game not in PROFILES: raise ValueError('Unknown game profile')
 if not request.strip(): raise ValueError('Request is empty')
 matched=[{'category':name,'steps':steps} for name,keys,steps in RULES if any(k in request.lower() for k in keys)]
 if not matched: matched=[{'category':'general','steps':['inspect project and dependencies','specify desired record changes','review staged diff','validate and test']}]
 return {'game':game,'request':request,'mode':'deterministic template planner (no AI model connected)','status':'proposal only','workstreams':matched,'approval_required':True,'writes_game_files':False}
