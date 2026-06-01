#!/usr/bin/env python3
"""Generate images with gpt-image-2 from a text prompt.

Usage:
    python generate.py "your prompt here"
    python generate.py --prompt-file prompts/before_after.txt
    python generate.py "a prompt" --size 1024x1024 --n 2 --out output/

Reads OPENAI_API_KEY from .env (or the environment).
Saves PNGs to the output/ directory with a timestamped name.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from imagegen.env import load_env
from imagegen.run import run_job

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate images with gpt-image-2")
    parser.add_argument("prompt", nargs="?", help="Text prompt")
    parser.add_argument("--prompt-file", help="Read the prompt from a file instead")
    parser.add_argument("--image", action="append",
                        help="Reference image(s) for image-to-image / edit mode. Repeatable.")
    parser.add_argument("--size", default="1024x1024",
                        help="1024x1024, 1536x1024 (landscape), 1024x1536 (portrait), or auto")
    parser.add_argument("--n", type=int, default=1, help="How many images to generate")
    parser.add_argument("--quality", default="high", choices=["low", "medium", "high", "auto"])
    parser.add_argument("--moderation", default="auto", choices=["auto", "low"],
                        help="'low' = less restrictive filtering (useful for clinical/medical imagery)")
    parser.add_argument("--preamble", help="File whose text is prepended to the prompt (e.g. a realism preamble)")
    parser.add_argument("--out", default="output", help="Output directory")
    args = parser.parse_args()

    load_env(ROOT / ".env")
    if not os.environ.get("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set. Add it to .env", file=sys.stderr)
        return 1

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text().strip()
    elif args.prompt:
        prompt = args.prompt
    else:
        print("ERROR: provide a prompt or --prompt-file", file=sys.stderr)
        return 1

    if args.preamble:
        preamble = Path(args.preamble).read_text().strip()
        prompt = f"{preamble}\n\n{prompt}"

    run_job(
        prompt=prompt,
        images=args.image,
        size=args.size,
        n=args.n,
        quality=args.quality,
        moderation=args.moderation,
        out=ROOT / args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
