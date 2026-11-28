"""Explicit record-linked voice manifests and safe offline batch production."""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import json
import re
import subprocess
import tempfile
import wave
from . import audio

_BAD = re.compile(r'[<>:"|?*\\\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}

def stem(value):
    if not isinstance(value, str):
        raise ValueError("voice stem must be text")
    parts = value.split("/")
    if len(parts) != 3 or any(not x or x in (".", "..") or _BAD.search(x) or x.endswith((" ", ".")) or x.split(".")[0].upper() in _RESERVED for x in parts):
        raise ValueError("expected safe plugin/voice-type/response stem")
    if not parts[0].lower().endswith((".esm", ".esp", ".esl")) or parts[-1].lower().endswith((".wav", ".lip", ".xwm", ".fuz")):
        raise ValueError("invalid plugin or response stem")
    return PurePosixPath(*parts)

def load_manifest(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("game") not in ("Skyrim", "Fallout4") or not isinstance(obj.get("lines"), list):
        raise ValueError("expected Skyrim/Fallout4 voice manifest")
    seen, rows = set(), []
    for row in obj["lines"]:
        if not isinstance(row, dict):
            raise ValueError("invalid line")
        key = str(stem(row.get("stem")))
        if key.casefold() in seen:
            raise ValueError("duplicate voice stem: " + key)
        seen.add(key.casefold())
        for field in ("record", "text"):
            if not isinstance(row.get(field), str):
                raise ValueError("record and text must be explicit strings")
        if not row["record"].strip():
            raise ValueError("record identity required")
        rows.append(dict(row, stem=key))
    return {"game": obj["game"], "lines": rows}

def audit(root, manifest):
    inventory = audio.inventory(Path(root), [r["stem"] for r in manifest["lines"]])
    existing = {r["key"]: r for r in inventory["lines"]}
    rows = []
    for line in manifest["lines"]:
        item = existing.get(line["stem"].casefold(), {})
        status = "missing"
        if item.get("has_fuz"):
            status = "packed" if item.get("has_lip_payload") else "packed-no-lip"
        elif item.get("has_audio"):
            status = "source-ready" if item.get("has_lip_payload") else "needs-lip"
        rows.append({**line, "status": status, "files": item.get("files", {})})
    return {"game": manifest["game"], "lines": rows, "errors": inventory["errors"],
            "unlisted": sorted(set(existing) - {r["stem"].casefold() for r in manifest["lines"]})}

def safe_path(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError("path escapes workspace")
    return path

def batch_pack(root, output, manifest, *, encoder=None, ffmpeg=None,
               lip_tool=None, fonix=None, allow_no_lip=False, execute=False):
    root, output = Path(root).resolve(strict=True), Path(output).resolve()
    if output == root or output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError("source and output trees must be disjoint")
    report = audit(root, manifest)
    results = []
    for row in report["lines"]:
        name = row["stem"]
        target = safe_path(output, name + ".fuz")
        item = {"stem": name, "record": row["record"], "target": str(target)}
        try:
            if target.exists():
                raise ValueError("destination exists")
            files = row["files"]
            def source(ext):
                f = files.get(ext, {})
                return safe_path(root, f["path"]) if f and not f.get("error") else None
            packed, xwm, wav, lip = (source(x) for x in (".fuz", ".xwm", ".wav", ".lip"))
            if packed:
                operation = "copy-fuz"
                _, existing_xwm = audio.unpack_fuz(packed.read_bytes())
                if not allow_no_lip and not audio.unpack_fuz(packed.read_bytes())[0]:
                    raise ValueError("source FUZ has no LIP; unpack and provide a LIP source first")
            else:
                if not xwm and not (wav and encoder):
                    raise ValueError("need XWM or WAV plus encoder")
                if not lip and not allow_no_lip and not (wav and lip_tool and fonix and row["text"].strip()):
                    raise ValueError("need LIP or WAV, native LIP backend, Fonix and transcript")
                operation = "pack" if xwm else "encode-and-pack"
                if not lip and lip_tool and wav and fonix:
                    operation += "+generate-lip"
            item["operation"] = operation
            if execute:
                with tempfile.TemporaryDirectory() as td:
                    temp = Path(td)
                    if packed:
                        blob = packed.read_bytes()
                        audio.unpack_fuz(blob)
                    else:
                        if not xwm:
                            xwm = temp / "voice.xwm"
                            audio.convert(wav, xwm, encoder, "encode")
                        if not lip and lip_tool and wav and fonix:
                            source_wav = wav
                            info = audio.wav_info(wav.read_bytes())
                            if (info["channels"], info["sample_width"], info["sample_rate"]) != (1, 2, 16000):
                                if not ffmpeg:
                                    raise ValueError("non-normalized WAV requires FFmpeg")
                                source_wav = temp / "normalized.wav"
                                audio.convert(wav, source_wav, ffmpeg, "normalize")
                            lip = temp / "voice.lip"
                            audio.native_lip(source_wav, lip, lip_tool, Path(fonix), manifest["game"], row["text"])
                        blob = audio.pack_fuz(xwm.read_bytes(), lip.read_bytes() if lip else b"")
                    if not allow_no_lip and not audio.unpack_fuz(blob)[0]:
                        raise ValueError("missing LIP")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    audio.publish(safe_path(output, name + ".fuz"), blob)
            item["status"] = "written" if execute else "planned"
        except (ValueError, OSError, EOFError, wave.Error, subprocess.SubprocessError) as exc:
            item.update(status="blocked", error=str(exc))
        results.append(item)
    return {"execute": execute, "results": results, "inventory_errors": report["errors"]}

def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="chimster-voice")
    p.add_argument("operation", choices=("audit", "batch"))
    p.add_argument("root", type=Path)
    p.add_argument("manifest", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--encoder"); p.add_argument("--ffmpeg")
    p.add_argument("--lip-tool"); p.add_argument("--fonix", type=Path)
    p.add_argument("--allow-no-lip", action="store_true")
    p.add_argument("--execute", action="store_true")
    a = p.parse_args(argv)
    manifest = load_manifest(a.manifest)
    if a.operation == "audit":
        result = audit(a.root, manifest)
    else:
        if not a.output:
            p.error("batch requires --output")
        result = batch_pack(a.root, a.output, manifest, encoder=a.encoder, ffmpeg=a.ffmpeg,
                            lip_tool=a.lip_tool, fonix=a.fonix, allow_no_lip=a.allow_no_lip, execute=a.execute)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if any(r.get("status") == "blocked" for r in result.get("results", [])):
        raise SystemExit(1)

if __name__ == "__main__":
    main()
