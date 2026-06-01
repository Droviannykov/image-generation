"""Controlled vocabulary + compatibility rules for the reference library.

A closed vocab makes auto-tagging, retrieval, and the coherence check deterministic.
Any value the tagger emits that isn't listed is coerced to "unknown".
"""
from __future__ import annotations

# Axes that map to an actual reference-image slot, in keep-priority order.
# identity is mandatory and always Reference 1. Film/look is NOT a slot (post-process).
REF_AXES = ["identity", "background", "makeup", "pose"]

MAX_REFS = 4  # gpt-image-2 blends; 2-4 is the practical sweet spot, not 16.

# Allowed tag values per descriptive axis (identity is free-text {present, descr}).
ALLOWED = {
    "background": [
        "home_bathroom", "home_bedroom", "living_room", "kitchen",
        "studio_gray", "studio_white", "outdoor_urban", "outdoor_nature",
        "cafe", "office", "plain_wall", "unknown",
    ],
    "lighting": [
        "soft_window", "warm_window_soft", "warm_indoor", "harsh_daylight",
        "on_camera_flash", "studio_softbox", "clinical_even", "golden_hour",
        "overcast", "mixed_indoor", "unknown",
    ],
    "pose": [
        "front_selfie", "front_portrait", "three_quarter", "profile",
        "candid_offcamera", "over_shoulder", "seated", "unknown",
    ],
    "wardrobe": [
        "tshirt_casual", "knit_sweater", "blouse", "satin_blouse",
        "dress", "robe", "activewear", "unknown",
    ],
    "makeup": ["none", "natural", "everyday", "full_glam", "editorial", "unknown"],
    "camera_film": [
        "iphone_lofi", "smartphone_clean", "dslr_clean", "studio",
        "film_35mm", "unknown",
    ],
}

# Lighting families: refs from different families stapled together read as fake composites.
LIGHTING_FAMILY = {
    "soft_window": "soft", "warm_window_soft": "soft", "warm_indoor": "soft",
    "overcast": "soft", "mixed_indoor": "soft",
    "harsh_daylight": "harsh", "on_camera_flash": "harsh",
    "studio_softbox": "studio", "clinical_even": "studio", "studio": "studio",
    "golden_hour": "golden",
    "unknown": "unknown",
}


def coerce(axis: str, value: str) -> str:
    """Return value if it's in the allowed vocab for axis, else 'unknown'."""
    allowed = ALLOWED.get(axis)
    if allowed is None:
        return value
    return value if value in allowed else "unknown"


def lighting_compatible(a: str, b: str) -> bool:
    """True if two lighting tags belong to the same family (or either is unknown)."""
    fa, fb = LIGHTING_FAMILY.get(a, "unknown"), LIGHTING_FAMILY.get(b, "unknown")
    return "unknown" in (fa, fb) or fa == fb
