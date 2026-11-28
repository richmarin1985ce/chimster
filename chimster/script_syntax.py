"""Original, scoped syntax grammars shared by Chimster and Sublime export.

A deliberately bounded subset of Sublime syntax: ordered match/scope,
named push/pop contexts and meta_scope. No third-party grammar execution.
"""
import json
import re
from pathlib import Path
from functools import lru_cache

LANGUAGES = {
    "papyrus": ("Papyrus", ["psc"], "scriptname extends import function endfunction event endevent state endstate property endproperty auto autoreadonly native global conditional hidden mandatory debugonly betaonly if elseif else endif while endwhile return new as is struct endstruct group endgroup", "bool int float string var none", "true false none", False),
    "geck": ("GECK Script", ["gek", "geck"], "scn scriptname begin end if elseif else endif while loop foreach return break continue let set to eval call function endfunction ref short long float int string_var array_var", "ref short long float int string_var array_var", "true false", False),
    "oblivion": ("Oblivion Script", ["obscript"], "scn scriptname begin end if elseif else endif set to return while loop foreach let eval break continue", "short long float ref string_var array_var", "true false", False),
    "morrowind": ("Morrowind Script", ["mwscript"], "begin end if elseif else endif while endwhile set to return", "short long float", "", False),
    "lua": ("OpenMW Lua", ["lua"], "and break do else elseif end for function goto if in local not or repeat return then until while", "", "true false nil", True),
}
PROFILE = {"skyrim":"papyrus", "skyrimse":"papyrus", "skyrimae":"papyrus",
           "skyrimvr":"papyrus", "fallout4":"papyrus", "fallout4vr":"papyrus",
           "fallout3":"geck", "newvegas":"geck", "oblivion":"oblivion",
           "morrowind":"morrowind", "openmw":"lua"}

def language_for(game, filename=""):
    suffix = Path(filename).suffix.casefold()
    for key, spec in LANGUAGES.items():
        if suffix.lstrip(".") in spec[1]:
            return key
    return PROFILE.get(game.casefold(), "papyrus")

def words(items, sensitive):
    return ("" if sensitive else "(?i)") + r"\b(?:" + "|".join(map(re.escape, items.split())) + r")\b"

def rule(pattern, scope=None, **extra):
    return {"match":pattern, **({"scope":scope} if scope else {}), **extra}

def definition(language):
    title, extensions, keywords, types, literals, sensitive = LANGUAGES[language]
    main = []
    contexts = {"main":main}
    def block(name, start, end, scope):
        main.append(rule(start, scope, push=name))
        contexts[name] = [{"meta_scope":scope},rule(end, scope, pop=True)]
    if language == "papyrus":
        block("block_comment", r";/", r"/;", "comment.block")
        block("documentation", r"\{", r"\}", "comment.block.documentation")
    if language == "lua":
        # Explicit bounded long-bracket forms, including common equals levels.
        for level in range(5):
            eq = "="*level
            block("long_comment_"+str(level), re.escape("--["+eq+"["), re.escape("]"+eq+"]"), "comment.block")
            block("long_string_"+str(level), re.escape("["+eq+"["), re.escape("]"+eq+"]"), "string.quoted.other")
        main.append(rule(r"--[^\n]*", "comment.line.double-dash"))
    else:
        main.append(rule(r";[^\n]*", "comment.line.semicolon"))
    for quote, name in [('"',"double"), ("'","single")] if sensitive else [('"',"double")]:
        scope = "string.quoted."+name
        main.append(rule(re.escape(quote),scope,push=name))
        contexts[name] = [{"meta_scope":scope}, rule(r"\\.", "constant.character.escape"),
                          rule(re.escape(quote),scope,pop=True),
                          rule(r"$",pop=True)]
    for items,scope in [(types,"storage.type"),(literals,"constant.language"),(keywords,"keyword.control")]:
        if items:
            main.append(rule(words(items,sensitive),scope))
    main.extend([rule(r"\b(?:0[xX][0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b","constant.numeric"),
                 rule(r"\b[A-Za-z_]\w*(?=\s*\()","entity.name.function"),
                 rule(r"==|!=|<=|>=|&&|\|\||->|:=|[+\-*/%=<>!&|]","keyword.operator")])
    return {"name":"Chimster "+title,"file_extensions":extensions,
            "scope":"source."+language,"version":2,"contexts":contexts}

@lru_cache(maxsize=8)
def compiled(language):
    return {name:[(re.compile(r["match"]),r) for r in rules if "match" in r]
            for name,rules in definition(language)["contexts"].items()}

def spans(source, language):
    """Return nonoverlapping character offsets and scopes, line by line."""
    if len(source)>512*1024:
        raise ValueError("highlight limit: 512 Ki characters")
    grammar = definition(language)["contexts"]
    patterns = compiled(language)
    stack = ["main"]
    offset = 0
    for line in source.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        pos = 0
        while pos <= len(content):
            context = stack[-1]
            scope = grammar[context][0].get("meta_scope") if context!="main" else None
            hits = [(m.start(),i,m,r) for i,(pat,r) in enumerate(patterns[context])
                    if (m:=pat.search(content,pos)) is not None]
            if not hits:
                if scope and pos<len(content):
                    yield offset+pos,offset+len(content),scope
                break
            _,_,m,r = min(hits,key=lambda x:(x[0],x[1]))
            if scope and m.start()>pos:
                yield offset+pos,offset+m.start(),scope
            if m.end()>m.start() and (tag:=r.get("scope",scope)):
                yield offset+m.start(),offset+m.end(),tag
            if r.get("pop"):
                stack.pop()
            elif "push" in r:
                stack.append(r["push"])
            elif m.end()==pos:
                raise ValueError("zero-width rule without state transition")
            pos=m.end()
        offset+=len(line)

def export(language, output):
    """JSON-quoted YAML scalars avoid accidental escape interpretation."""
    spec=definition(language)
    lines=["%YAML 1.2","---","name: "+json.dumps(spec["name"]),
           "file_extensions: "+json.dumps(spec["file_extensions"]),
           "scope: "+spec["scope"],"version: 2","contexts:"]
    for name,rules in spec["contexts"].items():
        lines.append("  "+name+":")
        for item in rules:
            for i,(key,value) in enumerate(item.items()):
                lines.append(("    - " if i==0 else "      ")+key+": "+json.dumps(value))
    p=Path(output)
    if not p.name.endswith(".sublime-syntax"):
        raise ValueError("expected .sublime-syntax output")
    with p.open("x",encoding="utf-8") as out:
        out.write("\n".join(lines)+"\n")
    return str(p)
