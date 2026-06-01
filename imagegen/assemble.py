"""Assemble a role-labeled, indexed multi-reference prompt from a selection + spec."""
from __future__ import annotations

from dataclasses import dataclass

from . import paths
from .select import Selection

# What each reference slot should contribute — and, crucially, what to IGNORE,
# so a makeup/pose donor's face doesn't leak into the subject's identity.
ROLE_INSTRUCTIONS = {
    "identity": "IDENTITY — keep this person's exact face, bone structure, skin tone, "
                "and hair. The output must be unmistakably this same individual.",
    "background": "BACKGROUND only — reproduce this setting/background and its lighting. "
                  "IGNORE any people in it.",
    "makeup": "MAKEUP STYLE only — copy only the makeup look (eyes, lips, blush, finish). "
              "Do NOT copy this reference's face, identity, hair, or background.",
    "pose": "POSE only — copy only the body pose, head angle, and framing. "
            "Do NOT copy this reference's face, identity, clothing, or background.",
}


@dataclass
class AssembledJob:
    image_paths: list[str]
    prompt: str
    recommended_post: str | None
    warnings: list[str]


def _read_preamble() -> str:
    return paths.REALISM_PREAMBLE.read_text().strip() if paths.REALISM_PREAMBLE.exists() else ""


def assemble(selection: Selection, spec: dict) -> AssembledJob:
    """Build (ordered image list, prompt, recommended post-filter) for run_job."""
    lines: list[str] = []
    preamble = _read_preamble()
    if preamble:
        lines += [preamble, ""]

    n = len(selection.refs)
    lines.append(f"You are given {n} reference image(s). Use each ONLY for its stated role:")
    for idx, ref in enumerate(selection.refs, start=1):
        role = ROLE_INSTRUCTIONS.get(ref.axis, ref.axis.upper())
        descr = ""
        if ref.axis == "identity":
            ident = ref.record.get("axes", {}).get("identity", {})
            descr = f" ({ident.get('descr', '')})" if isinstance(ident, dict) else ""
        lines.append(f"  Reference {idx} = {role}{descr}")
    lines.append("")

    if spec.get("scene"):
        lines += [f"SCENE: {spec['scene']}", ""]
    if spec.get("preserve"):
        lines += [f"PRESERVE: {spec['preserve']}", ""]
    if spec.get("change_only"):
        lines += [f"CHANGE ONLY: {spec['change_only']}", ""]

    constraints = spec.get("constraints", "No text, no watermark, no border.")
    lines.append(f"CONSTRAINTS: {constraints}")

    prompt = "\n".join(lines)

    # Film/look is post-processing, never a reference slot.
    recommended_post = None
    if spec.get("camera_film") == "iphone_lofi":
        recommended_post = ("python3 scripts/iphone7_filter.py <output.png> "
                            "<output_lofi.png> --strength 1.0")

    return AssembledJob(
        image_paths=selection.image_paths,
        prompt=prompt,
        recommended_post=recommended_post,
        warnings=list(selection.warnings),
    )
