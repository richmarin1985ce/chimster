"""Initial standalone binary codecs; no third-party code."""
import struct

def pack_fuz(lip: bytes, audio: bytes, version: int = 1) -> bytes:
    if not audio:
        raise ValueError("missing audio")
    return struct.pack("<4sII", b"FUZE", version, len(lip)) + lip + audio

def unpack_fuz(blob: bytes) -> tuple[int, bytes, bytes]:
    if len(blob) < 12:
        raise ValueError("truncated FUZ")
    magic, version, size = struct.unpack_from("<4sII", blob)
    if magic != b"FUZE" or version != 1 or size >= len(blob) - 12:
        raise ValueError("unsupported or malformed FUZ")
    return version, blob[12:12+size], blob[12+size:]

def encode_strings(entries: dict[int, str], kind="STRINGS", encoding="utf-8") -> bytes:
    kind = kind.upper()
    if kind not in {"STRINGS", "DLSTRINGS", "ILSTRINGS"}:
        raise ValueError("unsupported table")
    directory, payload = bytearray(), bytearray()
    for key, text in sorted(entries.items()):
        raw = text.encode(encoding)
        if b"\0" in raw:
            raise ValueError("embedded NUL")
        raw += b"\0"
        directory += struct.pack("<II", key, len(payload))
        if kind != "STRINGS":
            payload += struct.pack("<I", len(raw))
        payload += raw
    return struct.pack("<II", len(entries), len(payload)) + directory + payload

def decode_strings(blob: bytes, kind="STRINGS", encoding="utf-8") -> dict[int, str]:
    kind = kind.upper()
    if kind not in {"STRINGS", "DLSTRINGS", "ILSTRINGS"} or len(blob) < 8:
        raise ValueError("invalid table")
    count, size = struct.unpack_from("<II", blob)
    start = 8 + 8*count
    if start + size != len(blob):
        raise ValueError("invalid table size")
    data = blob[start:]
    result = {}
    for i in range(count):
        key, off = struct.unpack_from("<II", blob, 8+8*i)
        if key in result or off >= size:
            raise ValueError("invalid key/offset")
        if kind == "STRINGS":
            end = data.find(b"\0", off)
            if end < 0:
                raise ValueError("unterminated string")
            raw = data[off:end]
        else:
            if off + 4 > size:
                raise ValueError("truncated length")
            length, = struct.unpack_from("<I", data, off)
            off += 4
            if length < 1 or off+length > size or data[off+length-1] != 0:
                raise ValueError("invalid string length")
            raw = data[off:off+length-1]
        result[key] = raw.decode(encoding)
    return result
