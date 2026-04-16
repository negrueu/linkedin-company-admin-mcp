"""Pure parsing helpers for LinkedIn HTML snippets.

These functions take a string of HTML (``page.content()`` output) and
return structured data. Isolating them from the browser makes the logic
testable with captured fixtures under ``tests/integration/fixtures/``.

When a helper grows complex, lift it into its own module. Keep each
function single-purpose and side-effect free.
"""

from __future__ import annotations

import re

_COUNT_SUFFIX_RE = re.compile(
    r"([\d.,]+)\s*([KMB])?\s*(?:followers?|connections?|employees?|members?)?",
    re.IGNORECASE,
)
_FOLLOWERS_RE = re.compile(
    r"([\d.,]+)\s*([KMB])?\s*followers?",
    re.IGNORECASE,
)


def parse_abbreviated_count(text: str) -> int | None:
    """Parse LinkedIn's abbreviated counts: ``"1,234"`` / ``"5.4K"`` / ``"2M"``.

    Returns ``None`` when no match is found.

    >>> parse_abbreviated_count("1,234 followers")
    1234
    >>> parse_abbreviated_count("5.4K")
    5400
    >>> parse_abbreviated_count("2M followers")
    2000000
    """
    match = _COUNT_SUFFIX_RE.search(text)
    if not match:
        return None
    raw_number, suffix = match.group(1), match.group(2)
    try:
        value = float(raw_number.replace(",", ""))
    except ValueError:
        return None
    multiplier = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get((suffix or "").upper(), 1)
    return int(value * multiplier)


def extract_followers_count(text: str) -> int | None:
    """Return the number that appears before the word ``followers`` in ``text``.

    >>> extract_followers_count("KETU AI SRL 1 follower")
    1
    >>> extract_followers_count("1.2K followers · 10 employees")
    1200
    """
    match = _FOLLOWERS_RE.search(text)
    if not match:
        return None
    return parse_abbreviated_count(match.group(0))


def parse_after_marker(
    text: str,
    marker: str,
    *,
    min_length: int = 1,
) -> str | None:
    """Return the first non-empty line strictly after ``marker``.

    Useful when LinkedIn stacks metadata ("<Author>\\n<Headline>\\nFollow\\n<Body>")
    and the discriminator between header and body is a fixed label like
    "Follow" or "Following".

    >>> parse_after_marker("John\\nCEO\\nFollow\\nBody goes here", "Follow")
    'Body goes here'
    >>> parse_after_marker("no marker here", "Follow") is None
    True
    """
    lines = [line.strip() for line in text.splitlines()]
    try:
        idx = lines.index(marker)
    except ValueError:
        return None
    for candidate in lines[idx + 1 :]:
        if len(candidate) >= min_length:
            return candidate
    return None


def is_empty_state(text: str, markers: tuple[str, ...]) -> bool:
    """True if any of the LinkedIn empty-state strings appears in ``text``."""
    lowered = text.lower()
    return any(m.lower() in lowered for m in markers)
