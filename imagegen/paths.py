"""Canonical paths for the project."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENV_FILE = ROOT / ".env"
PROMPTS_DIR = ROOT / "prompts"
REALISM_PREAMBLE = PROMPTS_DIR / "realism_preamble.txt"

IMAGES_DIR = ROOT / "images"
LIBRARY_DIR = IMAGES_DIR / "library"
INCOMING_DIR = IMAGES_DIR / "incoming"
REGISTRY = LIBRARY_DIR / "registry.json"

OUTPUT = ROOT / "output"
SPECS_DIR = ROOT / "specs"

META_SUFFIX = ".meta.json"  # sidecar: gen_xxx.png -> gen_xxx.png.meta.json
