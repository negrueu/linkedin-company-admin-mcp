"""Sqlite-backed persistent rate limit state.

The in-memory bucket in ``rate_limit.py`` is fine for a single process.
Users running the MCP on two machines against the same LinkedIn account,
or restarting their Claude Desktop between posts, need state that survives
across restarts. This module provides a tiny stdlib-only store.
"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

from linkedin_company_admin_mcp.core.exceptions import ConfigurationError


class SqliteRateLimitStore:
    """Append-only log of ``(key, timestamp)`` tuples.

    Uses ``time.monotonic()`` seconds as timestamp. We do NOT use wall
    clock because the sliding window must be monotonic; a user changing
    their system time mid-run shouldn't unlock extra calls.
    """

    __slots__ = ("_conn", "_lock", "_path")

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS rate_events (
        key TEXT NOT NULL,
        ts REAL NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_key_ts ON rate_events(key, ts);
    """

    def __init__(self, path: Path, *, create_parents: bool = True) -> None:
        self._path = path
        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        elif not path.parent.exists():
            raise ConfigurationError(f"rate limit db parent missing: {path.parent}")
        try:
            self._conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
        except sqlite3.Error as e:
            raise ConfigurationError(f"cannot open rate limit db {path}: {e}") from e
        self._conn.executescript(self._SCHEMA)
        self._lock = threading.Lock()

    def record(self, key: str, ts: float) -> None:
        with self._lock:
            self._conn.execute("INSERT INTO rate_events(key, ts) VALUES(?, ?)", (key, ts))

    def count_since(self, key: str, cutoff: float) -> int:
        with self._lock:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM rate_events WHERE key = ? AND ts >= ?",
                (key, cutoff),
            )
            (count,) = cur.fetchone()
            return int(count)

    def purge_before(self, cutoff: float) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM rate_events WHERE ts < ?", (cutoff,))

    def close(self) -> None:
        with self._lock:
            self._conn.close()
