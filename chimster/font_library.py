"""Local, content-addressed desktop font library; no OS or game installation."""
from pathlib import Path
from io import BytesIO
import hashlib
import os
import tempfile

MAX_BYTES = 32 * 1024 * 1024
EXTENSIONS = {".ttf", ".otf"}

def inspect_bytes(data):
    from fontTools.ttLib import TTFont
    from PIL import ImageFont
    if len(data) > MAX_BYTES:
        raise ValueError("Font exceeds 32 MiB limit")
    if data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        raise ValueError("Expected a single TTF or OTF font")
    try:
        with TTFont(BytesIO(data)) as font:
            if not any(t in font for t in ("glyf", "CFF ", "CFF2")):
                raise ValueError("Unsupported outline format")
            names = font["name"]
            info = {
                "family": names.getDebugName(16) or names.getDebugName(1) or "Unnamed",
                "style": names.getDebugName(17) or names.getDebugName(2) or "Regular",
                "characters": len(font.getBestCmap() or {}),
                "embedding_flags": font["OS/2"].fsType if "OS/2" in font else None,
                "license": names.getDebugName(13) or "Not declared",
                "format": "TTF" if "glyf" in font else "OTF",
            }
        ImageFont.truetype(BytesIO(data), 24).getmask("Aa")
    except Exception as exc:
        raise ValueError("Unreadable or unsupported font: " + str(exc)) from exc
    return info

def read_font(path):
    path = Path(path)
    if path.suffix.lower() not in EXTENSIONS or not path.is_file():
        raise ValueError("Choose a .ttf or .otf file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    return data, inspect_bytes(data)

class FontLibrary:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else Path.home() / ".chimster" / "fonts"

    def import_font(self, source):
        data, info = read_font(source)
        digest = hashlib.sha256(data).hexdigest()
        target = self.root / (digest + "." + info["format"].lower())
        self.root.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            # Stage and publish complete files; no source moves or OS installation.
            fd, name = tempfile.mkstemp(dir=self.root, suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as output:
                    output.write(data)
                os.replace(name, target)
            finally:
                Path(name).unlink(missing_ok=True)
        return target, info

    def entries(self):
        for path in sorted(self.root.glob("*")):
            if path.suffix.lower() in EXTENSIONS:
                try:
                    _, info = read_font(path)
                except (OSError, ValueError):
                    continue
                yield path, info

def drop_paths(widget, data):
    """TkDND sends a Tcl list, including braces around names containing spaces."""
    return tuple(Path(p) for p in widget.tk.splitlist(data))
