#!/usr/bin/env python3
"""Tag-driven renderer: spec -> select refs -> assemble prompt -> gpt-image-2 -> sidecar.

Usage:
    python3 scripts/render.py --spec specs/glowup_makeup.json            # render (spends API)
    python3 scripts/render.py --spec specs/glowup_makeup.json --dry-run  # zero API spend
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from imagegen import paths                 # noqa: E402
from imagegen.assemble import assemble     # noqa: E402
from imagegen.env import load_env          # noqa: E402
from imagegen.select import pick_refs      # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Render from a spec using the tagged library")
    ap.add_argument("--spec", required=True, help="path to a spec JSON file")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the assembled prompt + chosen refs, spend nothing")
    ap.add_argument("--out", default=str(paths.OUTPUT))
    args = ap.parse_args()

    load_env(paths.ENV_FILE)
    spec = json.loads(Path(args.spec).read_text())

    selection = pick_refs(spec, use_embeddings=not args.dry_run)
    job = assemble(selection, spec)

    print("=== chosen references ===")
    for idx, ref in enumerate(selection.refs, start=1):
        print(f"  Reference {idx}: {ref.axis:10} {ref.record.get('id','?'):8} {ref.record.get('path','')}")
    if job.warnings:
        print("=== warnings ===")
        for w in job.warnings:
            print(f"  ! {w}")
    print("\n=== assembled prompt ===")
    print(job.prompt)
    if job.recommended_post:
        print(f"\n=== recommended post-process ===\n  {job.recommended_post}")

    if args.dry_run:
        print("\n[dry-run] no API call made.")
        return 0

    if not selection.refs:
        print("ERROR: no references selected; cannot render.", file=sys.stderr)
        return 1

    from imagegen.run import run_job
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = run_job(
        prompt=job.prompt,
        images=job.image_paths,
        size=spec.get("size", "1024x1024"),
        n=spec.get("n", 1),
        quality=spec.get("quality", "high"),
        moderation=spec.get("moderation", "auto"),
        out=args.out,
        stamp=stamp,
    )

    # Provenance sidecar per output image.
    for path in saved:
        meta = {
            "spec_file": args.spec,
            "spec": spec,
            "references": [
                {"index": i + 1, "axis": r.axis, "id": r.record.get("id"),
                 "path": r.record.get("path"), "axes": r.record.get("axes")}
                for i, r in enumerate(selection.refs)
            ],
            "prompt": job.prompt,
            "model": "gpt-image-2",
            "size": spec.get("size", "1024x1024"),
            "quality": spec.get("quality", "high"),
            "moderation": spec.get("moderation", "auto"),
            "warnings": job.warnings,
            "recommended_post": job.recommended_post,
            "rendered_at": datetime.now(timezone.utc).isoformat(),
        }
        Path(str(path) + paths.META_SUFFIX).write_text(json.dumps(meta, indent=2))
        print(f"Sidecar -> {path}{paths.META_SUFFIX}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
