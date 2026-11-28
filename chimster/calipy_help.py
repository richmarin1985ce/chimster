"""Constrained local language and intent engine; no neural weights."""
from dataclasses import dataclass
import re
import textwrap
from .wiki_render import blocks, spans

STOP = set("a an the to of and for in how do i can what is my with please could you me about show tell help where does it should would want use make".split())
ALIASES = {"navmeshes": "navmesh", "navigation": "navmesh", "scripts": "script",
           "compiling": "compile", "compiler": "compile", "compilers": "compile",
           "quests": "quest", "textures": "texture", "plugins": "plugin",
           "worldspaces": "worldspace", "records": "record", "voices": "voice",
           "lods": "lod", "installing": "install", "installation": "install"}
PHRASES = {"level of detail": "lod", "path finding": "navmesh",
           "pathfinding": "navmesh", "lip sync": "lipsync", "load order": "loadorder"}

def terms(text):
    text = text.casefold()
    for phrase, token in PHRASES.items():
        text = text.replace(phrase, token)
    return {ALIASES.get(w, w) for w in re.findall(r"[a-z0-9]+", text) if w not in STOP}

@dataclass(frozen=True)
class Guide:
    page: str
    title: str
    section: str
    cards: tuple[str, ...]

def sections(body):
    heading, lines = "", []
    for kind, line in blocks(body):
        if kind.startswith("h"):
            if lines:
                yield heading, lines
            heading, lines = line, []
        elif line.strip():
            clean = line if kind == "code" else "".join(value for _, value, _ in spans(line))
            if kind == "bullet":
                clean = "• " + clean
            lines.append(clean)
    if lines:
        yield heading, lines

def make_cards(lines):
    cards = []
    for line in lines:
        cards.extend(textwrap.wrap(line, width=250, break_long_words=True,
                                   break_on_hyphens=False) or [line])
    return tuple(cards)

class LocalHelp:
    def __init__(self, wiki):
        self.wiki = wiki
        self.catalog = tuple(wiki.pages())

    def find(self, question, context=""):
        q = terms(question[:500])
        if not q:
            return ()
        ctx = terms(context)
        matches = []
        for page in self.catalog:
            name = terms(page["title"] + " " + page["id"])
            for heading, lines in sections(self.wiki.read(page["id"])["body"]):
                h = terms(heading)
                body = terms(" ".join(lines))
                found = q & (name | h | body)
                if not found:
                    continue
                score = (len(found)/len(q), len(q & h)*4 + len(q & name)*3
                         + len(q & body), len(ctx & (name | h)))
                matches.append((score, Guide(page["id"], page["title"], heading, make_cards(lines))))
        matches.sort(key=lambda pair: pair[0], reverse=True)
        result, seen = [], set()
        for score, guide in matches:
            if (guide.page, guide.section) in seen or not guide.cards:
                continue
            seen.add((guide.page, guide.section))
            result.append(guide)
            if len(result) == 5:
                break
        return tuple(result)
