"""Shared gpt-image-2 call + save logic (used by generate.py and scripts/render.py)."""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from openai import OpenAI

MODEL = "gpt-image-2"


def run_job(prompt: str, images=None, size: str = "1024x1024", n: int = 1,
            quality: str = "high", moderation: str = "auto",
            out: Path | str = "output", stamp: str | None = None) -> list[Path]:
    """Generate (text-only) or edit (with reference images) and save PNGs.

    images: list of file paths to use as references (edit mode). None/empty -> text-to-image.
    Returns the list of saved output paths.
    """
    client = OpenAI()
    images = list(images or [])

    if images:
        print(f"Editing from {len(images)} reference image(s) "
              f"-> {n} output(s) at {size} (quality={quality})...")
        files = [open(p, "rb") for p in images]
        try:
            result = client.images.edit(
                model=MODEL,
                image=files if len(files) > 1 else files[0],
                prompt=prompt,
                size=size,
                n=n,
                quality=quality,
                extra_body={"moderation": moderation},
            )
        finally:
            for f in files:
                f.close()
    else:
        print(f"Generating {n} image(s) at {size} (quality={quality})...")
        result = client.images.generate(
            model=MODEL,
            prompt=prompt,
            size=size,
            n=n,
            quality=quality,
            extra_body={"moderation": moderation},
        )

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = stamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    saved: list[Path] = []
    for i, item in enumerate(result.data):
        path = out_dir / f"gen_{stamp}_{i}.png"
        path.write_bytes(base64.b64decode(item.b64_json))
        print(f"Saved {path}")
        saved.append(path)
    return saved
