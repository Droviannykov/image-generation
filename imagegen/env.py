"""Minimal .env loader (lifted from generate.py so all entry points share it)."""
from __future__ import annotations

import os
from pathlib import Path


def load_env(env_path: Path) -> None:
    """Load KEY=VALUE lines from a .env file into the environment (no extra dep)."""
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
