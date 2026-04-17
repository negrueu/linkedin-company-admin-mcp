"""`--check-selectors` CLI exit codes."""

from __future__ import annotations

from datetime import date

import linkedin_company_admin_mcp.cli as cli
from linkedin_company_admin_mcp.selectors.staleness import SelectorEntry


def test_exits_zero_when_all_fresh(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "_collect_selector_entries",
        lambda: [SelectorEntry("FRESH", date.today())],
    )
    rc = cli.main(["--check-selectors", "--max-age-days", "60"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "all selectors fresh" in out.lower()


def test_exits_nonzero_when_stale_found(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        cli,
        "_collect_selector_entries",
        lambda: [SelectorEntry("STALE", date(2020, 1, 1))],
    )
    rc = cli.main(["--check-selectors", "--max-age-days", "60"])
    out = capsys.readouterr().out
    assert rc == 3
    assert "STALE" in out
