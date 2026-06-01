#!/usr/bin/env python3
"""Post-process an image to mimic an old iPhone 7 (2016) snapshot look.

Layers: resolution softening, smartphone oversharpening, flattened dynamic
range (lifted blacks / clipped highlights), cool-neutral white balance,
shadow-weighted luminance noise, a small saturation push, and JPEG recompression.

Usage:
    python scripts/iphone7_filter.py <in.png> <out.png>
    python scripts/iphone7_filter.py <in.png> <out.png> --strength 1.3
Tunable flags: --downscale --sharpen --noise --shadow-lift --cool --saturation --jpeg
"""
import argparse
import io

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--strength", type=float, default=1.0, help="global multiplier on the effect")
    ap.add_argument("--downscale", type=float, default=0.72, help="resolution-softening factor (down then up)")
    ap.add_argument("--sharpen", type=float, default=120, help="UnsharpMask percent (phone oversharpening)")
    ap.add_argument("--noise", type=float, default=7.0, help="luminance noise sigma (0-255 scale)")
    ap.add_argument("--shadow-lift", type=float, default=0.045, help="raise black point (flatter range)")
    ap.add_argument("--cool", type=float, default=0.03, help="cool white-balance shift (blue up / red down)")
    ap.add_argument("--saturation", type=float, default=1.08, help="saturation multiplier")
    ap.add_argument("--jpeg", type=int, default=82, help="JPEG recompression quality")
    ap.add_argument("--seed", type=int, default=7, help="noise seed (reproducible)")
    args = ap.parse_args()
    s = args.strength

    img = Image.open(args.inp).convert("RGB")
    w, h = img.size

    # 1) resolution softening: downscale then upscale
    ds = 1.0 - (1.0 - args.downscale) * s
    small = img.resize((max(1, int(w * ds)), max(1, int(h * ds))), Image.BICUBIC)
    img = small.resize((w, h), Image.BILINEAR)

    # 2) smartphone oversharpening
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=int(args.sharpen * s), threshold=2))

    x = np.asarray(img).astype(np.float32) / 255.0

    # 3) flatten dynamic range: lift blacks, gently clip highlights
    lift = args.shadow_lift * s
    x = x * (1.0 - lift) + lift            # raise black point + reduce contrast
    x = np.clip(x * 1.02, 0, 1)            # tiny highlight push toward clipping

    # 4) cool-neutral white balance
    c = args.cool * s
    x[..., 2] = np.clip(x[..., 2] * (1 + c), 0, 1)   # blue up
    x[..., 0] = np.clip(x[..., 0] * (1 - c * 0.6), 0, 1)  # red down

    # 5) shadow-weighted luminance noise
    rng = np.random.default_rng(args.seed)
    lum = x.mean(axis=2, keepdims=True)
    shadow_w = 0.5 + 0.5 * (1.0 - lum)     # more noise in darker areas
    noise = rng.normal(0, (args.noise * s) / 255.0, x.shape)
    x = np.clip(x + noise * shadow_w, 0, 1)

    img = Image.fromarray((x * 255).astype(np.uint8), "RGB")

    # 6) small saturation push (phones punch color)
    sat = 1.0 + (args.saturation - 1.0) * s
    img = ImageEnhance.Color(img).enhance(sat)

    # 7) JPEG recompression artifacts
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=args.jpeg)
    buf.seek(0)
    img = Image.open(buf).convert("RGB")

    img.save(args.out)
    print(f"Saved {args.out}  ({w}x{h}, strength={s})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
