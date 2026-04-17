"""Parse last-verified dates from the selectors registry."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from textwrap import dedent

from linkedin_company_admin_mcp.selectors.staleness import (
    SelectorEntry,
    find_stale,
    parse_selectors_file,
)


def test_parses_group_under_last_verified_comment(tmp_path: Path) -> None:
    src = tmp_path / "sel.py"
    src.write_text(
        dedent(
            '''
            """Docs."""

            # last verified 2026-03-01
            FOO = "#foo"
            BAR = "#bar"

            # last verified 2026-04-17
            BAZ = "#baz"
            '''
        ),
        encoding="utf-8",
    )
    entries = parse_selectors_file(src)
    assert entries == [
        SelectorEntry(name="FOO", last_verified=date(2026, 3, 1)),
        SelectorEntry(name="BAR", last_verified=date(2026, 3, 1)),
        SelectorEntry(name="BAZ", last_verified=date(2026, 4, 17)),
    ]


def test_ignores_constants_without_date(tmp_path: Path) -> None:
    src = tmp_path / "sel.py"
    src.write_text("COMPANY_BASE = 'x'\n", encoding="utf-8")
    assert parse_selectors_file(src) == []


def test_find_stale_filters_by_age() -> None:
    today = date(2026, 4, 17)
    entries = [
        SelectorEntry("FRESH", date(2026, 4, 1)),
        SelectorEntry("STALE", date(2026, 1, 1)),
    ]
    stale = find_stale(entries, today=today, max_age_days=60)
    assert [e.name for e in stale] == ["STALE"]
