"""Small original seed API catalog and bounded source symbol indexing.

No game files or third-party definitions bundled. Entries are advisory; exact
runtime support must be checked against installed versions. Unknown != invalid.
"""
from dataclasses import dataclass, asdict
import re
from .script_syntax import spans, PROFILE

@dataclass(frozen=True)
class Symbol:
    name: str
    signature: str
    description: str
    origin: str = "vanilla"
    owner: str = ""
    line: int = 0

PAPYRUS = (
    Symbol("GetStage","Int GetStage()","Current quest stage.",owner="Quest"),
    Symbol("SetStage","Bool SetStage(Int aiStage)","Attempt to set a quest stage.",owner="Quest"),
    Symbol("Start","Bool Start()","Attempt to start the quest.",owner="Quest"),
    Symbol("Stop","Stop()","Stop the quest.",owner="Quest"),
    Symbol("GetValue","Float GetValue(ActorValue akValue)","Read an actor value (Fallout 4).",owner="ObjectReference"),
)
SKYRIM = (
    Symbol("GetActorValue","Float GetActorValue(String asValueName)","Read an actor value.",owner="Actor"),
    Symbol("GetPlayer","Actor GetPlayer() Global","Return the player actor.",owner="Game"),
    Symbol("Wait","Wait(Float afSeconds) Global","Wait for the specified seconds.",owner="Utility"),
    Symbol("Trace","Trace(String asTextToPrint, Int aiSeverity = 0) Global","Write a Papyrus diagnostic trace.",owner="Debug"),
    Symbol("GetFormFromFile","Form GetFormFromFile(Int aiFormID, String asFilename) Global","Look up a form in a named plugin.",owner="Game"),
    Symbol("GetVersion","Int GetVersion() Global","Extender major version.","skse","SKSE"),
    Symbol("GetVersionMinor","Int GetVersionMinor() Global","Extender minor version.","skse","SKSE"),
)
FO4 = (
    Symbol("GetPlayer","Actor GetPlayer() Global","Return the player actor.",owner="Game"),
    Symbol("Wait","Wait(Float afSeconds) Global","Wait for the specified seconds.",owner="Utility"),
    Symbol("Trace","Trace(String asTextToPrint, Int aiSeverity = 0) Global","Write a Papyrus diagnostic trace.",owner="Debug"),
    Symbol("GetVersion","Int GetVersion() Global","Extender major version.","f4se","F4SE"),
)
LEGACY = (
    Symbol("GetStage","GetStage QuestID","Read quest stage."),
    Symbol("SetStage","SetStage QuestID Stage","Set quest stage."),
    Symbol("GetDistance","GetDistance ReferenceID","Distance to reference."),
    Symbol("GetDisabled","GetDisabled","Check whether reference is disabled."),
    Symbol("Enable","Enable","Enable reference."),
    Symbol("Disable","Disable","Disable reference."),
)
EXTENDERS = {
    "oblivion": (Symbol("GetOBSEVersion","GetOBSEVersion","Extender version.","obse"),),
    "fallout3": (Symbol("GetFOSEVersion","GetFOSEVersion","Extender version.","fose"),),
    "newvegas": (Symbol("GetNVSEVersion","GetNVSEVersion","Extender version.","xnvse"),),
}
MW = (
    Symbol("GetJournalIndex","GetJournalIndex QuestID","Read journal index."),
    Symbol("Journal","Journal QuestID Index","Add journal entry."),
    Symbol("MessageBox","MessageBox Text","Display a message."),
    Symbol("GetDistance","GetDistance ObjectID","Distance to object."),
)
LUA = (
    Symbol("print","print(...)","Write to the log.",owner=""),
    Symbol("require","require(moduleName)","Load a Lua module."),
    Symbol("pairs","pairs(table)","Iterate table entries."),
    Symbol("ipairs","ipairs(table)","Iterate sequential entries."),
    Symbol("getSimulationTime","getSimulationTime()","Current simulation time.",owner="openmw.core"),
)
SKY = {"skyrim","skyrimse","skyrimae","skyrimvr"}
FO = {"fallout4","fallout4vr"}

def catalog(game, language, extenders=()):
    game=game.casefold()
    if PROFILE.get(game)!=language:
        return ()
    enabled=set(extenders)
    if game in SKY:
        entries=tuple(s for s in PAPYRUS if s.name!="GetValue")+SKYRIM
    elif game in FO:
        entries=PAPYRUS+FO4
    elif game in EXTENDERS:
        entries=LEGACY+EXTENDERS[game]
    elif game=="morrowind":
        entries=MW
    elif game=="openmw":
        entries=LUA
    else:
        entries=()
    return tuple(s for s in entries if s.origin=="vanilla" or s.origin in enabled)

def masked(source,language):
    data=list(source)
    for a,b,scope in spans(source,language):
        if scope.startswith(("comment","string","constant.character.escape")):
            data[a:b]=[" " if c not in "\r\n" else c for c in source[a:b]]
    return "".join(data)

def local_symbols(source, language):
    clean=masked(source,language)
    result=[]
    owner=""
    for line,raw in enumerate(clean.splitlines(),1):
        s=raw.strip()
        if language=="papyrus":
            m=re.match(r"Scriptname\s+(\w+)",s,re.I)
            if m:owner=m[1];result.append(Symbol(owner,s,"Local script.","local",line=line));continue
            m=re.match(r"(?:[\w]+(?:\[\])?\s+)?(?:Function|Event|Property)\s+(\w+)",s,re.I)
        elif language=="lua":
            m=re.match(r"(?:local\s+)?function\s+([\w.:]+)",s)
        else:
            m=re.match(r"(?:scn|scriptname|short|long|float|ref|string_var|array_var)\s+(\w+)",s,re.I)
        if m:
            result.append(Symbol(m[1],s,"Declaration in current source.","local",owner,line))
    return tuple(result)

def complete(game,language,source,prefix,extenders=(),owner="",limit=40):
    if type(limit) is not int or not 1<=limit<=200:
        raise ValueError("invalid completion limit")
    norm=(lambda s:s) if language=="lua" else str.casefold
    prefix=norm(prefix)
    owner=norm(owner)
    items=local_symbols(source,language)+catalog(game,language,extenders)
    matches={}
    for symbol in items:
        if owner and norm(symbol.owner)!=owner:continue
        if not norm(symbol.name).startswith(prefix):continue
        key=(norm(symbol.owner),norm(symbol.name),symbol.origin)
        matches.setdefault(key,symbol)
    return sorted(matches.values(),key=lambda s:(s.origin!="local",norm(s.name),norm(s.owner)))[:limit]

def lookup(game,language,source,name,extenders=(),owner=""):
    norm=(lambda s:s) if language=="lua" else str.casefold
    return [s for s in complete(game,language,source,name,extenders,owner,200) if norm(s.name)==norm(name)]
