"""Local version control and explicit game launch primitives."""
from pathlib import Path
import subprocess

def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root.resolve()), *args], check=True, capture_output=True, text=True).stdout

def status(root: Path) -> str:
    return git(root, "status", "--short")

def checkpoint(root: Path, message: str, paths: list[str]) -> str:
    if not message.strip() or not paths:
        raise ValueError("explicit paths and commit message required")
    for item in paths:
        p = Path(item)
        if p.is_absolute() or ".." in p.parts or item in {".", ""}:
            raise ValueError("explicit relative path required")
    git(root, "--literal-pathspecs", "add", "--", *paths)
    git(root, "--literal-pathspecs", "commit", "--only", "-m", message, "--", *paths)
    return git(root, "rev-parse", "HEAD").strip()

def launch(executable: Path, args: list[str], cwd: Path | None = None):
    executable = executable.resolve(strict=True)
    if not executable.is_file():
        raise ValueError("not a file")
    return subprocess.Popen([str(executable), *args], cwd=str(cwd or executable.parent), shell=False)

def reload_guidance(game: str) -> str:
    return {
        "openmw": "reloadlua (Lua only)",
        "starfield": "ReloadScript <script> (compatible Papyrus edits only)",
        "falloutnv": "xNVSE CompileScript with forceRecompile for supported UDFs only"
    }.get(game.casefold(), "Restart game; no verified reload adapter.")
