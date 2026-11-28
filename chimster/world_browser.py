"""Read-only Creation Kit-style cell browser for New Vegas plugins.

Disk-local identities are resolved before applying last-wins overrides.
No plugin writes, asset loading, or claims of engine verification.
"""
from collections import defaultdict
from pathlib import Path
import struct
from math import isfinite, floor
from .native_parser import parse, subrecords
from .record_graph import Slots
from .loadorder import plugin_name

PLACED = {"REFR", "ACHR", "ACRE"}
KINDS = {"WRLD", "CELL", "LAND", "NAVM"} | PLACED


def label(key):
    return "" if key is None else f"{key.origin}:{key.local:06X}"


def text_field(raw):
    if not raw or not raw.endswith(b"\0") or b"\0" in raw[:-1]:
        return ""
    return raw[:-1].decode("cp1252", errors="replace")


def read_plugin(path):
    path = Path(path)
    nodes = parse("new-vegas", path.read_bytes())
    if not nodes or nodes[0].signature != b"TES4":
        raise ValueError(f"{path.name}: expected TES4 header")
    # MAST is repeatable; do not derive it from the dict.
    masters = [text_field(raw) for tag, raw in subrecords("new-vegas", nodes[0]) if tag == b"MAST"]
    if any(not name for name in masters):
        raise ValueError(f"{path.name}: invalid master name")
    if struct.unpack_from("<I", nodes[0].header, 8)[0] & 0x200:
        raise ValueError("Light plugins are not supported by the New Vegas browser")
    slots = Slots(path.name, masters)
    rows = []
    seen = set()

    def walk(items, world=None, cell=None, bucket=None):
        for node in items:
            if node.signature == b"GRUP":
                kind = struct.unpack_from("<i", node.header, 12)[0]
                owner = slots.decode(struct.unpack_from("<I", node.header, 8)[0]) if kind in (1, 6, 8, 9, 10) else None
                if kind == 1:
                    walk(node.children, owner, None, None)
                elif kind in (6, 8, 9, 10):
                    walk(node.children, world, owner, kind if kind in (8, 9, 10) else None)
                else:
                    walk(node.children, world, cell, bucket)
                continue
            if node.signature == b"TES4":
                continue
            flags, raw_id = struct.unpack_from("<II", node.header, 8)
            key = slots.decode(raw_id)
            if key is None or key in seen:
                raise ValueError(f"{path.name}: null or duplicate record identity {label(key)}")
            seen.add(key)
            sig = node.signature.decode("ascii", errors="replace")
            row = {"key": key, "signature": sig, "plugin": slots.names[-1], "flags": flags,
                   "world": world, "cell": cell, "bucket": bucket, "editor_id": "", "name": ""}
            # Only decode browser records and base record EDIDs. Opaque fields are never rewritten.
            if not flags & 0x20:
                parts = list(subrecords("new-vegas", node))
                fields = dict(parts)
                row["editor_id"] = text_field(fields.get(b"EDID"))
                if sig in KINDS:
                    row["name"] = text_field(fields.get(b"FULL"))
                if sig == "CELL":
                    grid = fields.get(b"XCLC", b"")
                    if len(grid) in (8, 12):
                        row["grid"] = struct.unpack_from("<2i", grid)
                    data = fields.get(b"DATA", b"")
                    row["interior"] = bool(data and data[0] & 1)
                if sig == "LAND" and b"VHGT" in fields:
                    row["height_raw"] = fields[b"VHGT"]
                if sig in PLACED:
                    scale = fields.get(b"XSCL", b"")
                    if len(scale) == 4:
                        value = struct.unpack("<f", scale)[0]
                        if isfinite(value) and value > 0:
                            row["scale"] = value
                    base = fields.get(b"NAME", b"")
                    if len(base) == 4:
                        row["base"] = slots.decode(struct.unpack("<I", base)[0])
                    pos = fields.get(b"DATA", b"")
                    if len(pos) == 24:
                        values = struct.unpack("<6f", pos)
                        if all(isfinite(x) for x in values):
                            row["position"], row["rotation"] = values[:3], values[3:]
                    row["persistent"] = bool(flags & 0x400) or bucket == 8
            rows.append(row)
    walk(nodes)
    return slots.names[-1], slots.names[:-1], rows


class Browser:
    def __init__(self, plugins):
        self.winners = {}
        self.history = defaultdict(list)
        self.issues = []
        loaded = set()
        for name, masters, rows in plugins:
            name = plugin_name(name)
            if name in loaded or any(master not in loaded for master in masters):
                raise ValueError(f"{name}: duplicate plugin or missing/late master")
            loaded.add(name)
            for row in rows:
                key = row["key"]
                old = self.winners.get(key)
                if old and old["signature"] != row["signature"]:
                    raise ValueError(f"{label(key)}: override changes record type")
                self.history[key].append(row["plugin"])
                self.winners[key] = row
        self.active = {k: r for k, r in self.winners.items() if not r["flags"] & 0x20}
        self.worlds = {k: r for k, r in self.active.items() if r["signature"] == "WRLD"}
        self.cells = defaultdict(list)
        self.children = defaultdict(list)
        self.coordinates = defaultdict(list)
        self.persistent_by_grid = defaultdict(list)
        for key, row in self.active.items():
            sig = row["signature"]
            if sig == "CELL":
                world = row["world"]
                if world is not None and world not in self.worlds:
                    self.issues.append(f"Missing world: {label(key)}")
                self.cells[world].append(row)
                if "grid" in row and world is not None:
                    self.coordinates[world, row["grid"]].append(row)
            elif sig in PLACED or sig in ("LAND", "NAVM"):
                owner = row["cell"]
                if owner not in self.active or self.active[owner]["signature"] != "CELL":
                    self.issues.append(f"Missing cell: {label(key)}")
                else:
                    self.children[owner].append(row)
                    parent = self.active[owner]
                    if sig in PLACED and row.get("persistent") and row.get("position") and parent.get("world") is not None:
                        x, y, _ = row["position"]
                        self.persistent_by_grid[parent["world"], (floor(x/4096), floor(y/4096))].append(row)
        for (world, grid), rows in self.coordinates.items():
            if len(rows) > 1:
                self.issues.append(f"Duplicate coordinates {label(world)} {grid}")

    @classmethod
    def open(cls, paths):
        return cls(read_plugin(path) for path in paths)

    def name(self, row):
        return row.get("editor_id") or row.get("name") or label(row["key"])

    def matching(self, rows, query):
        query = query.strip().casefold()
        def search(row):
            base = self.active.get(row.get("base"))
            return " ".join((self.name(row), row.get("name", ""), label(row["key"]),
                             row["plugin"], row["signature"], str(row.get("grid", "")),
                             self.name(base) if base else label(row.get("base")))).casefold()
        return sorted((r for r in rows if not query or query in search(r)),
                      key=lambda r: (self.name(r).casefold(), r["key"]))

    def cell_rows(self, world, query=""):
        return self.matching(self.cells.get(world, ()), query)

    def object_rows(self, cell, query=""):
        return self.matching(self.children.get(cell, ()), query)

    def details(self, row):
        result = {k:v for k,v in row.items() if k != "height_raw"}
        if "height_raw" in row:
            result["height_bytes"] = len(row["height_raw"])
        for field in ("key", "world", "cell", "base"):
            if field in result:
                result[field] = label(result[field])
        result["providers"] = list(self.history[row["key"]])
        base = self.active.get(row.get("base"))
        if base:
            result["base_name"] = self.name(base)
        return result
