"""Fragment binding inventory. Does not rewrite VMAD or generate wrappers."""
from dataclasses import dataclass
from pathlib import PurePosixPath
import json

@dataclass(frozen=True)
class Fragment:
    plugin: str
    owner: str
    kind: str
    event: str
    script: str
    function: str
    source: str

    def validate(self):
        if not all((self.plugin, self.owner, self.event, self.script, self.function)):
            raise ValueError("incomplete binding")
        if self.kind not in {"quest", "dialogue", "scene", "package", "perk", "terminal"}:
            raise ValueError("unknown fragment kind")
        p = PurePosixPath(self.source.replace("\\", "/"))
        if p.is_absolute() or ".." in p.parts or ":" in str(p) or p.suffix.lower() != ".psc":
            raise ValueError("invalid relative Papyrus path")

def inventory(items: list[Fragment]) -> str:
    seen = set()
    for f in items:
        f.validate()
        key = (f.plugin.casefold(), f.owner.casefold(), f.kind, f.event)
        if key in seen:
            raise ValueError("duplicate owner/event binding")
        seen.add(key)
    return json.dumps([vars(f) for f in sorted(items, key=lambda f:(f.plugin,f.owner,f.kind,f.event))], indent=2) + "\n"
