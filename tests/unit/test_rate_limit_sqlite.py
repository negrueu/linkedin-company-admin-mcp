"""Sqlite-backed rate limit store."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from linkedin_company_admin_mcp.core.rate_limit_sqlite import SqliteRateLimitStore


def test_records_and_counts_within_window(tmp_path: Path) -> None:
    store = SqliteRateLimitStore(tmp_path / "rl.db")
    now = time.monotonic()
    store.record("company_create_post", now - 10.0)
    store.record("company_create_post", now - 5.0)
    assert store.count_since("company_create_post", now - 60.0) == 2


def test_ignores_events_outside_window(tmp_path: Path) -> None:
    store = SqliteRateLimitStore(tmp_path / "rl.db")
    now = time.monotonic()
    store.record("x", now - 5000.0)
    store.record("x", now - 10.0)
    assert store.count_since("x", now - 60.0) == 1


def test_purge_removes_old_events(tmp_path: Path) -> None:
    store = SqliteRateLimitStore(tmp_path / "rl.db")
    now = time.monotonic()
    store.record("x", now - 5000.0)
    store.record("x", now - 10.0)
    store.purge_before(now - 60.0)
    assert store.count_since("x", 0.0) == 1


def test_keys_isolated(tmp_path: Path) -> None:
    store = SqliteRateLimitStore(tmp_path / "rl.db")
    now = time.monotonic()
    store.record("a", now)
    store.record("b", now)
    store.record("b", now)
    assert store.count_since("a", now - 1.0) == 1
    assert store.count_since("b", now - 1.0) == 2


def test_survives_reopen(tmp_path: Path) -> None:
    path = tmp_path / "rl.db"
    now = time.monotonic()
    SqliteRateLimitStore(path).record("k", now)
    assert SqliteRateLimitStore(path).count_since("k", now - 1.0) == 1


def test_bad_path_surfaces_configuration_error(tmp_path: Path) -> None:
    from linkedin_company_admin_mcp.core.exceptions import ConfigurationError

    with pytest.raises(ConfigurationError):
        SqliteRateLimitStore(tmp_path / "missing_dir" / "nested" / "rl.db", create_parents=False)
