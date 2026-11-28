"""Capability gates for callers; no implied retail certification."""
from .native_profiles import PROFILES

def capabilities(profile):
    p=PROFILES[profile]
    active=profile!="oblivion-remastered"
    return {
        "structural_read":active,
        "dependency_audit":active,
        "runtime_identity":active and not p.experimental and p.family!="TES3",
        "typed_reference_schema":active and p.schema_revision=="fnv-generated-v1",
        "native_creation_templates":active and profile in ("morrowind","new-vegas"),
        "native_formid_allocation":active and profile in ("fallout3","new-vegas"),
        "archive_read":active,
        "archive_packaging":active,
        "archive_pair_packaging":active and profile in ("fallout4","fallout4-vr"),
        "archive_cubemap_packaging":active and profile in ("fallout4","fallout4-vr"),
        "archive_precedence_preview":active,
        "external_archive_comparison":active,
        "retail_verified":False,
    }

def require(profile,operation):
    if not capabilities(profile).get(operation,False):
        raise ValueError(f"{operation} unavailable for {profile}")
