"""Snapshot capture helper."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from linkedin_company_admin_mcp.core.debug_snapshot import (
    capture_snapshot,
    snapshot_dir,
)


def test_snapshot_dir_is_under_profile_parent(tmp_path: Path) -> None:
    profile = tmp_path / ".linkedin-company-admin" / "profile"
    profile.mkdir(parents=True)
    d = snapshot_dir(profile)
    assert d == profile.parent / "debug-snapshots"


async def test_capture_snapshot_writes_html_and_png(tmp_path: Path) -> None:
    page = MagicMock()
    page.url = "https://www.linkedin.com/company/106949933/admin/"
    page.content = AsyncMock(return_value="<html>hello</html>")
    page.screenshot = AsyncMock()

    paths = await capture_snapshot(page, snapshot_dir=tmp_path, label="test_case")

    assert paths.html.exists()
    assert paths.html.read_text(encoding="utf-8") == "<html>hello</html>"
    assert paths.html.name.startswith("test_case_")
    assert paths.html.name.endswith(".html")
    page.screenshot.assert_awaited_once()


async def test_capture_snapshot_scrubs_bad_label() -> None:
    page = MagicMock()
    page.url = "https://x.com/"
    page.content = AsyncMock(return_value="x")
    page.screenshot = AsyncMock()

    with tempfile.TemporaryDirectory() as d:
        paths = await capture_snapshot(
            page, snapshot_dir=Path(d), label="../../etc/passwd"
        )
        assert paths.html.resolve().parent == Path(d).resolve()
