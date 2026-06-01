#!/usr/bin/env python3
"""Composite N images side by side, with optional captions above each panel.

Usage:
    python scripts/composite.py <in1> <in2> [<in3> ...] <out.png> [--gutter 12]
                                [--labels "Before|+ Skincare|+ Makeup"]
The last positional path is the output; all preceding paths are inputs (left->right).
Heights are matched to the shortest input, so inputs may differ in resolution.
"""
import argparse

from PIL import Image, ImageDraw, ImageFont


def load_font(size: int):
    for path in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="input paths... then the output path (last)")
    ap.add_argument("--gutter", type=int, default=12)
    ap.add_argument("--labels", default="", help="caption per panel, separated by |")
    ap.add_argument("--match", choices=["min", "max"], default="min",
                    help="match all panels to the shortest (min) or tallest (max) input height")
    args = ap.parse_args()

    *inputs, out_path = args.paths
    if len(inputs) < 1:
        ap.error("need at least one input and an output path")

    imgs = [Image.open(p).convert("RGB") for p in inputs]
    h = (min if args.match == "min" else max)(im.height for im in imgs)
    imgs = [im if im.height == h else im.resize((round(im.width * h / im.height), h)) for im in imgs]

    labels = args.labels.split("|") if args.labels else []
    strip = 0
    font = None
    if labels:
        strip = max(48, h // 22)
        font = load_font(int(strip * 0.5))

    total_w = sum(im.width for im in imgs) + args.gutter * (len(imgs) - 1)
    canvas = Image.new("RGB", (total_w, h + strip), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    x = 0
    for i, im in enumerate(imgs):
        canvas.paste(im, (x, strip))
        if labels and i < len(labels):
            text = labels[i].strip()
            bbox = draw.textbbox((0, 0), text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((x + (im.width - tw) / 2, (strip - th) / 2 - bbox[1]),
                      text, fill=(20, 20, 20), font=font)
        x += im.width + args.gutter

    canvas.save(out_path)
    print(f"Saved {out_path}  ({canvas.width}x{canvas.height})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
