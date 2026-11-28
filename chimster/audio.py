"""Native voice containers and opt-in local audio tools. No bundled SDK."""
from __future__ import annotations

import argparse
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import wave


def xwma_info(data: bytes) -> dict:
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"XWMA":
        raise ValueError("expected RIFF/XWMA, not WAV or ASF")
    if struct.unpack_from("<I", data, 4)[0] + 8 != len(data):
        raise ValueError("invalid RIFF size")
    chunks = {}
    pos = 12
    while pos < len(data):
        if len(data) - pos < 8:
            raise ValueError("truncated RIFF chunk header")
        name, n = struct.unpack_from("<4sI", data, pos)
        start = pos + 8
        end = start + n
        pos = end + (n & 1)
        if pos > len(data) or name in chunks and name in (b"fmt ", b"data", b"dpds"):
            raise ValueError("truncated or duplicate RIFF chunk")
        chunks[name] = memoryview(data)[start:end]
    fmt = chunks.get(b"fmt ", b"")
    if len(fmt) < 16 or not chunks.get(b"data"):
        raise ValueError("missing format or audio payload")
    tag, channels, rate, avg, align, bits = struct.unpack_from("<HHIIHH", fmt)
    if tag not in (0x161, 0x162) or channels not in (1, 2) or not rate or not avg or not align:
        raise ValueError("unsupported xWMA format")
    dpds = chunks.get(b"dpds")
    if dpds is not None:
        if not len(dpds) or len(dpds) % 4:
            raise ValueError("invalid seek table size")
        values = [v[0] for v in struct.iter_unpack("<I", dpds)]
        if values[0] == 0 or any(b < a for a, b in zip(values, values[1:])):
            raise ValueError("nonmonotonic seek table")
    return {"format_tag": tag, "channels": channels, "sample_rate": rate,
            "audio_bytes": len(chunks[b"data"]), "has_seek_table": dpds is not None}


def unpack_fuz(data: bytes) -> tuple[bytes, bytes]:
    if len(data) < 12:
        raise ValueError("truncated FUZ header")
    magic, version, n = struct.unpack_from("<4sII", data)
    if magic != b"FUZE" or version != 1 or n > len(data) - 12:
        raise ValueError("unsupported FUZ header or truncated LIP")
    lip, xwm = data[12:12+n], data[12+n:]
    xwma_info(xwm)
    return lip, xwm


def pack_fuz(xwm: bytes, lip: bytes = b"") -> bytes:
    xwma_info(xwm)
    return struct.pack("<4sII", b"FUZE", 1, len(lip)) + lip + xwm


def wav_info(data: bytes) -> dict:
    with wave.open(io.BytesIO(data), "rb") as f:
        n, channels, width, rate = f.getnframes(), f.getnchannels(), f.getsampwidth(), f.getframerate()
        if n <= 0 or len(f.readframes(n)) != n * channels * width:
            raise ValueError("empty or truncated WAV")
        return {"channels": channels, "sample_rate": rate, "sample_width": width,
                "frames": n, "duration": n / rate}


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    ext = path.suffix.lower()
    if ext == ".fuz":
        lip, xwm = unpack_fuz(data)
        return {"format": "fuz", "lip_bytes": len(lip), **xwma_info(xwm)}
    if ext == ".xwm":
        return {"format": "xwm", **xwma_info(data)}
    if ext == ".wav":
        return {"format": "wav", **wav_info(data)}
    raise ValueError("unsupported audio extension")


def inventory(root: Path, expected: list[str] | None = None) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("voice root must be a directory")
    groups = {}
    errors = []
    for p in sorted(root.rglob("*")):
        if p.is_symlink() or not p.is_file() or p.suffix.lower() not in (".wav", ".xwm", ".lip", ".fuz"):
            continue
        if not p.resolve().is_relative_to(root):
            continue
        rel = p.relative_to(root).as_posix()
        key = p.relative_to(root).with_suffix("").as_posix().casefold()
        files = groups.setdefault(key, {})
        ext = p.suffix.lower()
        if ext in files:
            errors.append({"path": rel, "error": "case-insensitive duplicate"})
            continue
        entry = {"path": rel, "bytes": p.stat().st_size}
        try:
            if ext != ".lip":
                entry.update(inspect(p))
            elif not entry["bytes"]:
                raise ValueError("empty LIP")
        except (ValueError, OSError, EOFError, wave.Error) as e:
            entry["error"] = str(e)
            errors.append({"path": rel, "error": str(e)})
        files[ext] = entry
    lines = []
    for key, files in sorted(groups.items()):
        valid = lambda ext: ext in files and "error" not in files[ext]
        native = valid(".fuz")
        audio = native or valid(".xwm") or valid(".wav")
        lip = (native and files[".fuz"]["lip_bytes"] > 0) or valid(".lip")
        lines.append({"key": key, "files": files, "has_audio": audio,
                      "has_lip_payload": lip, "has_fuz": native})
    wanted = {x.replace(chr(92), "/").casefold() for x in (expected or [])}
    present = {x["key"] for x in lines if x["has_audio"]}
    return {"lines": lines, "missing": sorted(wanted - present), "errors": errors}


def publish(path: Path, data: bytes) -> None:
    # Exclusive creation prevents accidental replacement of originals.
    with path.open("xb") as f:
        f.write(data)


def discover() -> dict:
    return {name: shutil.which(name) for name in
            ("ffmpeg", "ffprobe", "xWMAEncode", "WMAEncodeRS", "rhubarb", "FaceFXWrapper")}


def executable(path: str) -> str:
    found = shutil.which(path)
    if not found:
        raise ValueError("local executable not found: " + path)
    return str(Path(found).resolve())


def run_tool(args: list[str], timeout: float = 180) -> None:
    subprocess.run(args, check=True, timeout=timeout, shell=False, capture_output=True)


def convert(source: Path, target: Path, tool: str, mode: str) -> None:
    source = source.resolve(strict=True)
    if mode == "decode":
        xwma_info(source.read_bytes())
        suffix = ".wav"
    elif mode == "encode":
        wav_info(source.read_bytes())
        suffix = ".xwm"
    elif mode == "normalize":
        wav_info(source.read_bytes())
        suffix = ".wav"
    else:
        raise ValueError("unknown conversion mode")
    if target.suffix.lower() != suffix:
        raise ValueError("incorrect output extension")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / ("output" + suffix)
        exe = executable(tool)
        if mode == "encode":
            args = [exe, str(source), str(out)]
        else:
            args = [exe, "-nostdin", "-v", "error", "-i", str(source)]
            if mode == "normalize":
                args += ["-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le"]
            args += [str(out)]
        run_tool(args)
        data = out.read_bytes()
        (xwma_info if mode == "encode" else wav_info)(data)
        publish(target, data)


def validate_cues(result: dict, duration: float) -> None:
    cues = result.get("mouthCues")
    if not isinstance(cues, list) or not cues:
        raise ValueError("missing mouth cues")
    previous = 0.0
    for cue in cues:
        a, b = float(cue["start"]), float(cue["end"])
        if not math.isfinite(a) or not math.isfinite(b) or a < previous or b <= a or b > duration + .03:
            raise ValueError("invalid cue timing")
        if cue["value"] not in tuple("ABCDEFGHX"):
            raise ValueError("unknown Rhubarb mouth shape")
        previous = b


def preview_lips(source: Path, target: Path, tool: str, transcript: str | None = None) -> None:
    source = source.resolve(strict=True)
    duration = wav_info(source.read_bytes())["duration"]
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "cues.json"
        args = [executable(tool), "-f", "json", "-o", str(out)]
        if transcript is not None:
            text = Path(td) / "dialogue.txt"
            text.write_text(transcript, encoding="utf-8")
            args += ["--dialogFile", str(text)]
        run_tool(args + [str(source)])
        result = json.loads(out.read_text(encoding="utf-8"))
        validate_cues(result, duration)
        publish(target, json.dumps(result, indent=2).encode("utf-8"))


def native_lip(source: Path, target: Path, tool: str, fonix: Path,
               game: str, transcript: str, language: str = "USEnglish") -> None:
    if game not in ("Skyrim", "Fallout4") or not transcript.strip():
        raise ValueError("explicit supported game and transcript required")
    if target.suffix.lower() != ".lip":
        raise ValueError("expected .lip output")
    source = source.resolve(strict=True)
    fonix = fonix.resolve(strict=True)
    info = wav_info(source.read_bytes())
    if (info["channels"], info["sample_width"], info["sample_rate"]) != (1, 2, 16000):
        raise ValueError("normalize to 16 kHz mono PCM16 first")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "output.lip"
        run_tool([executable(tool), game, language, str(fonix), str(source), str(out), transcript])
        data = out.read_bytes()
        if not data:
            raise ValueError("empty LIP output")
        # Backend-produced bytes remain unverified until game testing.
        publish(target, data)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m chimster.audio")
    s = p.add_subparsers(dest="op", required=True)
    s.add_parser("discover")
    a = s.add_parser("inspect"); a.add_argument("source", type=Path)
    a = s.add_parser("inventory"); a.add_argument("root", type=Path); a.add_argument("--expected", type=Path)
    a = s.add_parser("pack"); a.add_argument("source", type=Path); a.add_argument("target", type=Path); a.add_argument("--lip", type=Path)
    a = s.add_parser("unpack"); a.add_argument("source", type=Path); a.add_argument("directory", type=Path)
    for mode in ("encode", "decode", "normalize", "preview"):
        a = s.add_parser(mode); a.add_argument("source", type=Path); a.add_argument("target", type=Path); a.add_argument("--tool", required=True)
        if mode == "preview":
            a.add_argument("--transcript")
    a = s.add_parser("native-lip"); a.add_argument("source", type=Path); a.add_argument("target", type=Path)
    a.add_argument("--tool", required=True); a.add_argument("--fonix", required=True, type=Path)
    a.add_argument("--game", choices=("Skyrim", "Fallout4"), required=True); a.add_argument("--transcript", required=True)
    a.add_argument("--language", default="USEnglish")
    args = p.parse_args(argv)
    try:
        if args.op == "discover":
            print(json.dumps(discover(), indent=2))
        elif args.op == "inspect":
            print(json.dumps(inspect(args.source), indent=2))
        elif args.op == "inventory":
            wanted = json.loads(args.expected.read_text(encoding="utf-8")) if args.expected else None
            if wanted is not None and (not isinstance(wanted, list) or not all(isinstance(x, str) for x in wanted)):
                raise ValueError("expected manifest must be a JSON array of relative stems")
            print(json.dumps(inventory(args.root, wanted), indent=2))
        elif args.op == "pack":
            publish(args.target, pack_fuz(args.source.read_bytes(), args.lip.read_bytes() if args.lip else b""))
        elif args.op == "unpack":
            lip, xwm = unpack_fuz(args.source.read_bytes())
            # Require a new directory to prevent partial replacement.
            args.directory.mkdir()
            publish(args.directory / (args.source.stem + ".xwm"), xwm)
            if lip:
                publish(args.directory / (args.source.stem + ".lip"), lip)
        elif args.op == "preview":
            preview_lips(args.source, args.target, args.tool, args.transcript)
        elif args.op == "native-lip":
            native_lip(args.source, args.target, args.tool, args.fonix, args.game, args.transcript, args.language)
        else:
            convert(args.source, args.target, args.tool, args.op)
    except (ValueError, OSError, EOFError, wave.Error, subprocess.SubprocessError) as exc:
        p.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
