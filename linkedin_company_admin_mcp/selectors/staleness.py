"""Parse ``# last verified YYYY-MM-DD`` comments from selectors registry."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

_DATE_RE = re.compile(r"#\s*last verified\s+(\d{4})-(\d{2})-(\d{2})", re.IGNORECASE)
_NAME_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]+)\s*=\s*")


@dataclass(frozen=True, slots=True)
class SelectorEntry:
    name: str
    last_verified: date


def parse_selectors_file(path: Path) -> list[SelectorEntry]:
    """Walk the file top-to-bottom, tracking the most-recent date comment.

    Every subsequent ``NAME = ...`` assignment is tagged with that date
    until a new ``# last verified`` comment appears.
    """
    entries: list[SelectorEntry] = []
    current: date | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _DATE_RE.search(line)
        if m:
            y, mo, d = (int(x) for x in m.groups())
            current = date(y, mo, d)
            continue
        if current is None:
            continue
        nm = _NAME_RE.match(line)
        if nm:
            entries.append(SelectorEntry(name=nm.group(1), last_verified=current))
    return entries


def find_stale(
    entries: list[SelectorEntry],
    *,
    today: date | None = None,
    max_age_days: int,
) -> list[SelectorEntry]:
    """Return entries older than ``max_age_days`` vs ``today`` (default now)."""
    today = today or datetime.now().date()
    return [e for e in entries if (today - e.last_verified).days > max_age_days]
