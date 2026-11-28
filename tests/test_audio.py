import io
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from chimster import audio


def chunk(tag, body):
    return tag + struct.pack("<I", len(body)) + body + (b"\0" if len(body) % 2 else b"")


def xwm():
    # Synthetic structural fixture, not decodable WMA audio.
    fmt = struct.pack("<HHIIHH", 0x161, 1, 22050, 4000, 16, 16)
    payload = b"XWMA" + chunk(b"fmt ", fmt) + chunk(b"dpds", struct.pack("<II", 16, 32)) + chunk(b"data", b"0" * 32)
    return b"RIFF" + struct.pack("<I", len(payload)) + payload


def wav():
    out = io.BytesIO()
    with wave.open(out, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)
        f.writeframes(b"\0" * 32000)
    return out.getvalue()


class AudioTests(unittest.TestCase):
    def test_fuz_roundtrip(self):
        for lip in (b"", b"synthetic"):
            packed = audio.pack_fuz(xwm(), lip)
            self.assertEqual(audio.unpack_fuz(packed), (lip, xwm()))
            self.assertEqual(packed[:4], b"FUZE")

    def test_reject_invalid(self):
        for data in (b"", b"FUZE", b"FUZE" + struct.pack("<II", 2, 0) + xwm(),
                     b"FUZE" + struct.pack("<II", 1, 999) + xwm()):
            with self.assertRaises(ValueError):
                audio.unpack_fuz(data)
        with self.assertRaises(ValueError):
            audio.pack_fuz(wav())
        with self.assertRaises(ValueError):
            audio.xwma_info(xwm()[:-1])

    def test_inventory_and_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            voice = root / "Example.esp" / "VoiceType"
            voice.mkdir(parents=True)
            (voice / "Line.fuz").write_bytes(audio.pack_fuz(xwm(), b"lip"))
            (voice / "Bad.fuz").write_bytes(b"bad")
            result = audio.inventory(root, ["Example.esp/VoiceType/Line", "Example.esp/VoiceType/Missing"])
            self.assertEqual(result["missing"], ["example.esp/voicetype/missing"])
            self.assertEqual(len(result["errors"]), 1)
            self.assertTrue(next(x for x in result["lines"] if x["key"].endswith("/line"))["has_lip_payload"])

    def test_wav_and_cues(self):
        self.assertEqual(audio.wav_info(wav())["duration"], 1)
        good = {"mouthCues": [{"start": 0, "end": .5, "value": "A"}, {"start": .5, "end": 1, "value": "X"}]}
        audio.validate_cues(good, 1)
        good["mouthCues"][1]["start"] = .4
        with self.assertRaises(ValueError):
            audio.validate_cues(good, 1)

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "out.fuz"
            audio.publish(p, b"original")
            with self.assertRaises(FileExistsError):
                audio.publish(p, b"replacement")
            self.assertEqual(p.read_bytes(), b"original")

    def test_encoder_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, target = root / "source.wav", root / "output.xwm"
            source.write_bytes(wav())
            def fake(args):
                Path(args[-1]).write_bytes(xwm())
            with patch.object(audio, "executable", return_value="fake"), patch.object(audio, "run_tool", side_effect=fake):
                audio.convert(source, target, "fake", "encode")
            self.assertEqual(target.read_bytes(), xwm())

    def test_native_lip_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, target, fonix = root / "source.wav", root / "output.lip", root / "FonixData.cdf"
            source.write_bytes(wav())
            fonix.write_bytes(b"synthetic")
            def fake(args):
                self.assertEqual(args[1], "Skyrim")
                self.assertEqual(args[-1], "Hello.")
                Path(args[-2]).write_bytes(b"synthetic lip")
            with patch.object(audio, "executable", return_value="fake"), patch.object(audio, "run_tool", side_effect=fake):
                audio.native_lip(source, target, "fake", fonix, "Skyrim", "Hello.")
            self.assertEqual(target.read_bytes(), b"synthetic lip")


if __name__ == "__main__":
    unittest.main()
