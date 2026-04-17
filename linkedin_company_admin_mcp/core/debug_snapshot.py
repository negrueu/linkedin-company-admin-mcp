"""Debug snapshot capture.

When enabled via ``--debug-snapshot`` (or env LINKEDIN_DEBUG_SNAPSHOT),
any tool error triggers a best-effort capture of the current page HTML
and a PNG screenshot. Files land in ``<profile-parent>/debug-snapshots/``
so the session cookies directory stays untouched.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from patchright.async_api import Page

_log = logging.getLogger(__name__)

_SAFE_LABEL = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True, slots=True)
class SnapshotPaths:
    """Absolute paths to files written by ``capture_snapshot``."""

    html: Path
    png: Path


def snapshot_dir(profile_dir: Path) -> Path:
    """Return (but do not create) the snapshot directory for a profile."""
    return profile_dir.parent / "debug-snapshots"


def _safe_label(label: str) -> str:
    scrubbed = _SAFE_LABEL.sub("_", label).strip("._-")
    return scrubbed or "snapshot"


async def capture_snapshot(
    page: "Page",
    *,
    snapshot_dir: Path,
    label: str,
) -> SnapshotPaths:
    """Write ``<label>_<ts>.html`` and ``.png`` to ``snapshot_dir``.

    Returns the paths. Caller is responsible for logging them back to the
    user so they know where the evidence landed.
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"{_safe_label(label)}_{ts}"
    html_path = snapshot_dir / f"{stem}.html"
    png_path = snapshot_dir / f"{stem}.png"

    try:
        html = await page.content()
        html_path.write_text(html, encoding="utf-8")
    except Exception:
        _log.exception("failed to capture HTML snapshot")
    try:
        await page.screenshot(path=str(png_path), full_page=True)
    except Exception:
        _log.exception("failed to capture PNG screenshot")

    _log.warning(
        "debug snapshot saved: %s (url=%s)", stem, getattr(page, "url", "?")
    )
    return SnapshotPaths(html=html_path, png=png_path)
