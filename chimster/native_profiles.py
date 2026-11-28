"""Explicit format profiles. Disk-local and runtime FormIDs are distinct.

Only FNV generated schemas have extraction support here. Other profiles
describe identity/header conventions, not complete record coverage.
"""
from dataclasses import dataclass
from .record_graph import Identity
from .loadorder import plugin_name

@dataclass(frozen=True)
class Profile:
    name: str
    family: str
    record_header: int
    group_header: int | None
    light_runtime: bool
    schema_revision: str | None = None
    experimental: bool = False

PROFILES = {
    p.name: p for p in (
        Profile("morrowind", "TES3", 16, None, False),
        Profile("oblivion", "TES4", 20, 20, False),
        Profile("oblivion-remastered", "TES4", 20, 20, False),
        Profile("fallout3", "FO3", 24, 24, False),
        Profile("new-vegas", "FNV", 24, 24, False, "fnv-generated-v1"),
        Profile("skyrim", "TES5", 24, 24, False),
        Profile("skyrim-se", "TES5SE", 24, 24, True),
        Profile("skyrim-vr", "TES5VR", 24, 24, False, experimental=True),
        Profile("fallout4-vr", "FO4VR", 24, 24, False, experimental=True),
        Profile("fallout4", "FO4", 24, 24, True),
    )
}

# Legacy desktop/tool identifiers and explicit SE/AE edition aliases.
PROFILE_ALIASES = {
    "newvegas": "new-vegas", "skyrimse": "skyrim-se",
    "skyrimae": "skyrim-se", "skyrim-ae": "skyrim-se",
    "skyrimvr": "skyrim-vr", "fallout4vr": "fallout4-vr",
    "oblivionremastered": "oblivion-remastered",
}

def canonical_profile(value):
    if not isinstance(value, str):
        raise ValueError("invalid game profile")
    key = value.strip().casefold()
    key = PROFILE_ALIASES.get(key, key)
    if key not in PROFILES:
        raise ValueError("unknown game profile: " + value)
    return key

def active_profiles():
    return tuple(p for p in PROFILES if p != "oblivion-remastered")

@dataclass(frozen=True, order=True)
class Tes3Key:
    """Logical named TES3 key, not a universal identity for placed objects."""
    signature: str
    editor_id: str
    def __post_init__(self):
        if len(self.signature) != 4 or not self.signature.isascii():
            raise ValueError("invalid signature")
        if not self.editor_id or "\0" in self.editor_id:
            raise ValueError("invalid editor ID")
        object.__setattr__(self, "editor_id", self.editor_id.lower())

class RuntimeSlots:
    """Explicit full and light runtime tables; never use for on-disk decoding."""
    def __init__(self, profile, full=(), light=()):
        profile = canonical_profile(profile)
        if profile not in active_profiles():
            raise ValueError("runtime slots unavailable for deferred profile")
        self.profile = PROFILES[profile]
        if self.profile.experimental:raise ValueError("Runtime slot conventions not verified for this profile")
        if self.profile.family == "TES3":
            raise ValueError("TES3 has no runtime FormID table")
        self.full = tuple(plugin_name(x) for x in full)
        self.light = tuple(plugin_name(x) for x in light)
        if self.light and not self.profile.light_runtime:
            raise ValueError("light plugins unsupported")
        limit = 254 if self.profile.light_runtime else 255
        names = self.full + self.light
        if len(self.full) > limit or len(self.light) > 4096 or len(set(names)) != len(names):
            raise ValueError("invalid runtime table")
        self.full_index = {name: i for i, name in enumerate(self.full)}
        self.light_index = {name: i for i, name in enumerate(self.light)}

    def decode(self, raw):
        if type(raw) is not int or not 0 <= raw <= 0xffffffff:
            raise ValueError("invalid runtime ID")
        if not raw:
            return None
        slot = raw >> 24
        if slot == 255:
            raise ValueError("dynamic runtime ID has no persistent plugin identity")
        if slot == 254 and self.profile.light_runtime:
            index = (raw >> 12) & 0xfff
            if index >= len(self.light):
                raise ValueError("unknown light slot")
            return Identity(self.light[index], raw & 0xfff)
        if slot >= len(self.full):
            raise ValueError("unknown full slot")
        return Identity(self.full[slot], raw & 0xffffff)

    def encode(self, identity):
        if identity is None:
            return 0
        if identity.origin in self.light_index:
            if identity.local > 0xfff:
                raise ValueError("light object ID exceeds 12 bits")
            return 0xfe000000 | self.light_index[identity.origin] << 12 | identity.local
        if identity.origin in self.full_index:
            return self.full_index[identity.origin] << 24 | identity.local
        raise ValueError("unknown origin")

def inspect_profile(profile, signature, parts, slots):
    """Fail closed rather than inherit FNV field offsets into another game."""
    from .schema_reference import inspect
    parts = list(parts)
    if PROFILES[canonical_profile(profile)].schema_revision != "fnv-generated-v1":
        return [], tuple(range(len(parts)))
    return inspect(signature, parts, slots)


def capability_manifest():
    """Describe implemented format infrastructure, not retail certification."""
    return {"version":3,"pending_profiles":[],"deferred_profiles":["arena","daggerfall","oblivion-remastered","starfield","fallout76"],"profiles":[
        {"id":p.name,"release_scope":"deferred" if p.name=="oblivion-remastered" else "active","family":p.family,"record_header":p.record_header,
         "group_header":p.group_header,"light_runtime":p.light_runtime,
         "identity_kind":"named-subset" if p.family=="TES3" else "plugin-relative",
         "generated_schema":p.schema_revision,
         "experimental":p.experimental,"structural_read":p.name in active_profiles(),"runtime_slots_verified":False,"retail_verified":False}
        for p in PROFILES.values()]}
