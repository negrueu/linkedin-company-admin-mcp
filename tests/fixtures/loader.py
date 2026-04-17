"""Load synthetic HTML fixtures for selector-resolution tests."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).parent / "synthetic"


def load(name: str) -> str:
    """Return the HTML content of a synthetic fixture by stem."""
    path = _ROOT / f"{name}.html"
    if not path.is_file():
        raise FileNotFoundError(f"no synthetic fixture named {name!r} at {path}")
    return path.read_text(encoding="utf-8")
