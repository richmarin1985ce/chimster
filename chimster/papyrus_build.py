"""Explicit local Papyrus compilation, with staged output and header checks.

External binaries are trusted user-installed tools, not sandboxed. No runtime
installation, game launches, downloads, or native record modifications.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess
import tempfile
from .integrations import executable, file, directory, fresh
from .script_lint import check_file

FAMILIES = {
    "skyrim": ("skyrim", ">", 1), "skyrimle": ("skyrim", ">", 1),
    "skyrimse": ("skyrim", ">", 1), "skyrimae": ("skyrim", ">", 1),
    "skyrimvr": ("skyrim", ">", 1),
    "fallout4": ("fallout4", "<", 2), "fallout4vr": ("fallout4", "<", 2),
}

def family(game):
    try:
        return FAMILIES[game.casefold()]
    except (KeyError, AttributeError):
        raise ValueError("unsupported active Papyrus profile") from None

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def inspect_pex(path, game):
    """Check the bounded PEX header, not instructions or engine compatibility."""
    p = file(path, {".pex"})
    if p.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("PEX too large")
    with p.open("rb") as stream:
        head = stream.read(16)
        _, endian, expected = family(game)
        if len(head) != 16:
            raise ValueError("truncated PEX header")
        magic, major, minor, target, stamp = struct.unpack(endian + "IBBHQ", head)
        if magic != 0xFA57C0DE or target != expected or major != 3:
            raise ValueError("PEX header does not match target family")
        fields = []
        for _ in range(3):
            raw = stream.read(2)
            if len(raw) != 2:
                raise ValueError("truncated PEX string length")
            n = struct.unpack(endian + "H", raw)[0]
            raw = stream.read(n)
            if len(raw) != n:
                raise ValueError("truncated PEX header string")
            fields.append(raw.decode("utf-8", errors="replace"))
        if len(stream.read(2)) != 2:
            raise ValueError("missing PEX string table")
    return {"game": game, "game_id": target, "version": [major, minor],
            "source": fields[0], "size": p.stat().st_size,
            "sha256": digest(p), "scope": "header only"}

def diagnostics(output):
    """Common CK/Caprica location syntax; retain every unmatched message."""
    result = []
    for line in output.splitlines():
        if not line.strip():
            continue
        match = re.match(r"^(.*?\.psc)\s*\((\d+)\s*,\s*(\d+)\)\s*:\s*(.*)$", line, re.I)
        if not match:
            match = re.match(r"^(.*?\.psc):(\d+):(\d+):\s*(.*)$", line, re.I)
        if match:
            path, row, column, message = match.groups()
            severity = "warning" if re.search(r"\bwarning\b", message, re.I) else "error"
            result.append({"file": path, "line": int(row), "column": int(column),
                           "severity": severity, "message": message})
        else:
            result.append({"severity": "info", "message": line})
    return result

def plan(game, backend, exe, source, flags, imports, output):
    target, _, _ = family(game)
    if backend not in {"ck", "caprica"}:
        raise ValueError("unsupported compiler backend")
    src = file(source, {".psc"})
    flag = file(flags, {".flg"})
    out = fresh(output)
    roots = list(dict.fromkeys([str(src.parent), *(str(directory(p)) for p in imports)]))
    if any(";" in p for p in roots):
        raise ValueError("semicolon in import directory")
    if any(out.is_relative_to(Path(p)) for p in roots):
        raise ValueError("build output must be outside source/import roots")
    if out.is_relative_to(flag.parent):
        raise ValueError("build output must be outside flags directory")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", src.stem):
        raise ValueError("only unnamespaced script filenames are supported")
    lint = check_file(src)
    if lint["script_names"] != [src.stem.casefold()]:
        raise ValueError("Scriptname must match filename; namespaces not supported")
    binary = executable(exe)
    if backend == "ck":
        args = [binary, str(src), "-i=" + ";".join(roots),
                "-o=" + str(out), "-f=" + str(flag)]
    else:
        args = [binary, str(src), "--game", target, "--output", str(out),
                "--flags", str(flag)]
        for root in roots:
            args.extend(["--import", root])
    return {"game": game, "backend": backend, "args": args, "source": str(src),
            "flags": str(flag), "output": str(out), "imports": roots,
            "source_sha256": digest(src), "flags_sha256": digest(flag),
            "compiler_sha256": digest(binary), "lint": lint,
            "scope": "preview; external compiler/runtime not verified"}

def build(game, backend, exe, source, flags, imports, output, *, execute=False, timeout=120):
    if type(timeout) is not int or not 1 <= timeout <= 900:
        raise ValueError("timeout must be between 1 and 900 seconds")
    preview = plan(game, backend, exe, source, flags, imports, output)
    if not execute:
        return preview
    out = Path(preview["output"])
    # Use a private sibling staging area. Only publish checked artifacts into
    # an exclusively created fresh destination; failures leave no build there.
    with tempfile.TemporaryDirectory(prefix=".chimster-script-", dir=out.parent) as temp:
        stage = Path(temp) / "compiled"
        stage.mkdir()
        args = [("-o=" + str(stage)) if x == "-o=" + str(out)
                else str(stage) if x == str(out) else x for x in preview["args"]]
        try:
            cp = subprocess.run(args, shell=False, cwd=temp, capture_output=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
        except subprocess.TimeoutExpired:
            return {**preview, "status": "timeout", "diagnostics": []}
        log = cp.stdout + "\n" + cp.stderr
        result = {**preview, "returncode": cp.returncode,
                  "diagnostics": diagnostics(log), "compiler_log": log}
        if cp.returncode:
            return {**result, "status": "compiler-failed"}
        candidates = list(stage.iterdir())
        pex = [p for p in candidates if p.suffix.casefold() == ".pex"]
        if len(pex) != 1 or pex[0].is_symlink() or not pex[0].is_file() or pex[0].stem.casefold() != Path(source).stem.casefold():
            return {**result, "status": "unexpected-output"}
        try:
            header = inspect_pex(pex[0], game)
        except ValueError as exc:
            return {**result, "status": "invalid-pex", "reason": str(exc)}
        if (digest(preview["source"]) != preview["source_sha256"] or
                digest(preview["flags"]) != preview["flags_sha256"] or
                digest(preview["args"][0]) != preview["compiler_sha256"]):
            return {**result, "status": "inputs-changed"}
        report = {**result, "status": "header-checked", "artifact": header,
                  "scope": "external compilation and PEX header check; no engine validation"}
        out.mkdir()
        try:
            artifact = out / pex[0].name
            with artifact.open("xb") as dst:
                dst.write(pex[0].read_bytes())
            manifest = out / "compile.json"
            with manifest.open("x", encoding="utf-8") as dst:
                json.dump(report, dst, indent=2)
        except Exception:
            for name in (pex[0].name, "compile.json"):
                (out / name).unlink(missing_ok=True)
            out.rmdir()
            raise
        return report
