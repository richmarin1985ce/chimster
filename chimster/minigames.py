"""Portable grid-adventure authoring and offline preview, not native holotapes."""
from pathlib import Path
import json,re,html
def validate(p):
    if not isinstance(p,dict) or set(p)!={"schema","id","title","map"} or p["schema"]!=1:raise ValueError("invalid game project")
    if not isinstance(p["id"],str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}",p["id"]):raise ValueError("invalid ID")
    if not isinstance(p["title"],str) or not 1<=len(p["title"])<=80:raise ValueError("invalid title")
    rows=p["map"]
    if not isinstance(rows,list) or not 3<=len(rows)<=40 or any(not isinstance(r,str) for r in rows):raise ValueError("invalid map")
    w=len(rows[0])
    if not 3<=w<=60 or any(len(r)!=w or set(r)-set("#.SCE") for r in rows):raise ValueError("invalid map cells")
    cells="".join(rows)
    if cells.count("S")!=1 or cells.count("E")!=1:raise ValueError("one start and exit required")
    start=next((x,y) for y,r in enumerate(rows) for x,c in enumerate(r) if c=="S")
    seen={start};queue=[start]
    for x,y in queue:
        for a,b in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if 0<=a<w and 0<=b<len(rows) and rows[b][a]!="#" and (a,b) not in seen:seen.add((a,b));queue.append((a,b))
    if any((x,y) not in seen for y,r in enumerate(rows) for x,c in enumerate(r) if c in "CE"):raise ValueError("unreachable collectible or exit")
    return p
def load(path):
    p=Path(path)
    if p.stat().st_size>65536:raise ValueError("game project too large")
    return validate(json.loads(p.read_text(encoding="utf-8")))
def preview(p):
    validate(p)
    data=json.dumps(p,ensure_ascii=True).replace("<",r"\u003c")
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Chimster game preview</title><style>body{background:#101a13;color:#8fffa8;font:16px monospace;text-align:center}pre{display:inline-block;text-align:left;line-height:1.2;font-size:clamp(8px,2.4vw,22px);border:2px solid;padding:10px}button{background:#172b1b;color:inherit;border:1px solid;padding:12px;margin:3px}button:focus{outline:2px solid white}</style><h1 id="title"></h1><pre id="screen"></pre><p id="status"></p><div><button data-move="0,-1">Up</button></div><div><button data-move="-1,0">Left</button><button data-move="0,1">Down</button><button data-move="1,0">Right</button></div><button id="reset">Restart</button><script>const P="""+data+""";let grid,x,y,left,won,moves;const title=document.getElementById('title'),screen=document.getElementById('screen'),status=document.getElementById('status');title.textContent=P.title;function draw(){screen.textContent=grid.map((r,j)=>r.map((c,i)=>i===x&&j===y?'@':c==='.'?' ':c).join('')).join('\\n');status.textContent=won?'ROUTE COMPLETE — '+moves+' moves':'Cargo remaining: '+left+' | Moves: '+moves}function reset(){grid=P.map.map(r=>r.split(''));left=0;won=false;moves=0;grid.forEach((r,j)=>r.forEach((c,i)=>{if(c==='S'){x=i;y=j;r[i]='.'}if(c==='C')left++}));draw()}function step(dx,dy){if(won)return;const a=x+dx,b=y+dy,c=grid[b]?.[a];if(!c||c==='#')return;x=a;y=b;moves++;if(c==='C'){left--;grid[y][x]='.'}if(c==='E'&&!left)won=true;draw()}document.querySelectorAll('[data-move]').forEach(b=>b.onclick=()=>step(...b.dataset.move.split(',').map(Number)));document.getElementById('reset').onclick=reset;document.addEventListener('keydown',e=>{const d={ArrowUp:[0,-1],ArrowDown:[0,1],ArrowLeft:[-1,0],ArrowRight:[1,0]}[e.key];if(d){e.preventDefault();step(...d)}});reset()</script></html>"""
def export(p,output):
    validate(p);d=Path(output);d.mkdir(parents=True,exist_ok=False)
    (d/"game.json").write_text(json.dumps(p,indent=2),encoding="utf-8")
    (d/"play.html").write_text(preview(p),encoding="utf-8")
    return {"output":str(d),"kind":"grid adventure","status":"standalone browser preview only; no native holotape yet"}
