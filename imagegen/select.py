"""Reference selection: tag filter -> embedding rank -> coherence check -> ordered refs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from . import paths, vocab

EMBED_MODEL = "text-embedding-3-small"


@dataclass
class SelectedRef:
    axis: str
    record: dict


@dataclass
class Selection:
    refs: list[SelectedRef] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def image_paths(self) -> list[str]:
        return [r.record["path"] for r in self.refs]


def load_registry() -> list[dict]:
    if not paths.REGISTRY.exists():
        return []
    return json.loads(paths.REGISTRY.read_text() or "[]")


def _cosine(a, b) -> float:
    import numpy as np
    a, b = np.asarray(a, dtype="float32"), np.asarray(b, dtype="float32")
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a @ b / (na * nb))


def _embed(text: str):
    from openai import OpenAI
    resp = OpenAI().embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


def _axis_value(record: dict, axis: str):
    val = record.get("axes", {}).get(axis)
    if isinstance(val, dict):  # identity = {present, descr}
        return val
    return val


def pick_refs(spec: dict, registry: list[dict] | None = None,
              use_embeddings: bool = True) -> Selection:
    """Select one reference per requested axis in spec['refs'].

    spec['refs'] maps axis -> {"tag": <value|None>, "query": <text>}.
    identity is mandatory, placed first, and only records with
    rights.usable_as_identity == True are eligible.
    """
    registry = registry if registry is not None else load_registry()
    sel = Selection()

    requested = spec.get("refs", {})
    if "identity" not in requested:
        sel.warnings.append("No identity ref requested — identity should be Reference 1.")

    # Keep-priority order, identity first.
    ordered_axes = [a for a in vocab.REF_AXES if a in requested]

    for axis in ordered_axes:
        ask = requested[axis] or {}
        tag = ask.get("tag")
        query = ask.get("query", "")

        candidates = []
        for rec in registry:
            if axis == "identity":
                ident = _axis_value(rec, "identity") or {}
                if not (ident.get("present") and rec.get("rights", {}).get("usable_as_identity")):
                    continue
            else:
                val = _axis_value(rec, axis)
                if tag and val != tag:
                    continue
            candidates.append(rec)

        if not candidates:
            sel.warnings.append(f"No candidate found for axis '{axis}' (tag={tag!r}).")
            continue

        if use_embeddings and query:
            qvec = _embed(query)
            candidates.sort(key=lambda r: _cosine(qvec, r.get("embedding", [])), reverse=True)
        # else: keep registry order (deterministic, zero-spend for --dry-run)

        sel.refs.append(SelectedRef(axis=axis, record=candidates[0]))

    # Enforce MAX_REFS, dropping lowest-priority (identity already first).
    if len(sel.refs) > vocab.MAX_REFS:
        dropped = sel.refs[vocab.MAX_REFS:]
        sel.refs = sel.refs[:vocab.MAX_REFS]
        for d in dropped:
            sel.warnings.append(f"Dropped '{d.axis}' ref (over MAX_REFS={vocab.MAX_REFS}).")

    sel.warnings.extend(check_compatibility(sel))
    return sel


def check_compatibility(sel: Selection) -> list[str]:
    """Warn (don't block) when selected refs come from mismatched lighting families."""
    warnings: list[str] = []
    lit = [(r.axis, r.record.get("axes", {}).get("lighting", "unknown")) for r in sel.refs]
    for i in range(len(lit)):
        for j in range(i + 1, len(lit)):
            (ax_i, li), (ax_j, lj) = lit[i], lit[j]
            if not vocab.lighting_compatible(li, lj):
                warnings.append(
                    f"Lighting mismatch: {ax_i}={li} vs {ax_j}={lj} "
                    f"(stapling different light families reads as a fake composite)."
                )
    return warnings
