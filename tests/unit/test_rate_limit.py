"""Rate limiter decorator."""

from __future__ import annotations

import asyncio

import pytest

from linkedin_company_admin_mcp.core.exceptions import RateLimitError
from linkedin_company_admin_mcp.core.rate_limit import (
    rate_limited,
    reset_buckets_for_tests,
)


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_buckets_for_tests()


async def test_allows_calls_under_limit() -> None:
    @rate_limited(key="test_under", max_per_hour=3)
    async def op() -> int:
        return 42

    results = await asyncio.gather(op(), op(), op())
    assert results == [42, 42, 42]


async def test_raises_on_exceeding_limit() -> None:
    @rate_limited(key="test_over", max_per_hour=2)
    async def op() -> None:
        pass

    await op()
    await op()
    with pytest.raises(RateLimitError, match="test_over"):
        await op()


async def test_separate_keys_have_separate_buckets() -> None:
    @rate_limited(key="test_key_a", max_per_hour=1)
    async def a() -> str:
        return "a"

    @rate_limited(key="test_key_b", max_per_hour=1)
    async def b() -> str:
        return "b"

    assert await a() == "a"
    assert await b() == "b"
    with pytest.raises(RateLimitError):
        await a()


async def test_persistent_mode_survives_bucket_reset(tmp_path) -> None:
    """When a store is configured, the count persists across bucket resets."""
    from linkedin_company_admin_mcp.core.rate_limit import configure_persistent_store
    from linkedin_company_admin_mcp.core.rate_limit_sqlite import SqliteRateLimitStore

    store = SqliteRateLimitStore(tmp_path / "rl.db")
    configure_persistent_store(store)

    @rate_limited(key="test_persist", max_per_hour=2)
    async def op() -> None:
        pass

    await op()
    await op()

    reset_buckets_for_tests()
    configure_persistent_store(store)

    with pytest.raises(RateLimitError):
        await op()

    configure_persistent_store(None)
