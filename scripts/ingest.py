#!/usr/bin/env python3
"""Ingest real reference images into the tagged library.

Flow: image -> sha256 dedupe -> OpenAI vision caption+tags -> caption embedding ->
append images/library/registry.json (atomic).

Usage:
    python3 scripts/ingest.py images/incoming/*.png
    python3 scripts/ingest.py path/to/img.jpg --rights owned --identity-ok
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from imagegen import paths, vocab          # noqa: E402
from imagegen.env import load_env          # noqa: E402

VISION_MODEL = "gpt-4o"
EMBED_MODEL = "text-embedding-3-small"

TAGGER_SYSTEM = (
    "You tag a single photo for a reference library used to generate photorealistic "
    "portraits. Return STRICT JSON only. Fields:\n"
    '  "caption": one concise sentence describing the photo.\n'
    '  "identity": {"present": bool (is there a clear human face?), '
    '"descr": short description of the person or "" if none}.\n'
    '  "background", "lighting", "pose", "wardrobe", "makeup", "camera_film": '
    "pick the SINGLE best-fitting value from the allowed lists; if unsure use "
    '"unknown".\n'
    "Allowed values:\n" + json.dumps(vocab.ALLOWED, indent=0)
)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def auto_tag(client, path: Path) -> dict:
    resp = client.chat.completions.create(
        model=VISION_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": TAGGER_SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": "Tag this photo."},
                {"type": "image_url", "image_url": {"url": data_uri(path)}},
            ]},
        ],
    )
    raw = json.loads(resp.choices[0].message.content)
    axes = {"identity": {
        "present": bool(raw.get("identity", {}).get("present", False)),
        "descr": str(raw.get("identity", {}).get("descr", "")),
    }}
    for axis in ("background", "lighting", "pose", "wardrobe", "makeup", "camera_film"):
        axes[axis] = vocab.coerce(axis, str(raw.get(axis, "unknown")))
    return {"caption": str(raw.get("caption", "")), "axes": axes}


def embed(client, text: str):
    return client.embeddings.create(model=EMBED_MODEL, input=text or "reference").data[0].embedding


def load_registry() -> list[dict]:
    if not paths.REGISTRY.exists():
        return []
    return json.loads(paths.REGISTRY.read_text() or "[]")


def write_registry(records: list[dict]) -> None:
    paths.REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    tmp = paths.REGISTRY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(records, indent=2))
    os.replace(tmp, paths.REGISTRY)


def next_id(records: list[dict]) -> int:
    nums = [int(r["id"].split("_")[-1]) for r in records if r.get("id", "").startswith("ref_")]
    return (max(nums) + 1) if nums else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest reference images into the tagged library")
    ap.add_argument("paths", nargs="+", help="image file paths (globs expanded by your shell)")
    ap.add_argument("--rights", default="owned",
                    choices=["owned", "licensed", "cc", "model_release", "UNKNOWN"])
    ap.add_argument("--identity-ok", action="store_true",
                    help="allow these faces to be used as identity anchors")
    ap.add_argument("--source", default="", help="provenance note stored per image")
    args = ap.parse_args()

    load_env(paths.ENV_FILE)
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set. Add it to .env", file=sys.stderr)
        return 1

    from openai import OpenAI
    client = OpenAI()

    records = load_registry()
    seen = {r.get("sha256") for r in records}
    paths.LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    usable_as_identity = args.rights == "owned" or args.identity_ok

    added = 0
    for raw in args.paths:
        src = Path(raw)
        if not src.exists():
            print(f"skip (missing): {src}", file=sys.stderr)
            continue
        digest = sha256_of(src)
        if digest in seen:
            print(f"skip (duplicate): {src}")
            continue

        rid = f"ref_{next_id(records):04d}"
        dest = paths.LIBRARY_DIR / f"{rid}{src.suffix.lower()}"
        shutil.copy2(src, dest)

        print(f"tagging {src.name} -> {rid} ...")
        tagged = auto_tag(client, dest)
        record = {
            "id": rid,
            "path": str(dest.relative_to(paths.ROOT)),
            "sha256": digest,
            "caption": tagged["caption"],
            "axes": tagged["axes"],
            "embedding": embed(client, tagged["caption"]),
            "embedding_kind": "caption-3small",
            "rights": {
                "consent": args.rights,
                "usable_as_identity": bool(usable_as_identity and tagged["axes"]["identity"]["present"]),
                "source": args.source,
                "notes": "",
            },
            "added": datetime.now(timezone.utc).isoformat(),
        }
        records.append(record)
        seen.add(digest)
        added += 1
        print(f"  caption: {tagged['caption']}")
        print(f"  axes: {tagged['axes']}")

    write_registry(records)
    print(f"\nDone. Added {added} record(s). Registry now holds {len(records)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
