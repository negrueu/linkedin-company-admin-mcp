"""In-process rate limiter.

Applied as a decorator on write-side tools. NOT a replacement for
LinkedIn's own server-side limits - it's a safety net so a buggy caller
doesn't spam requests and get the account warning.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from linkedin_company_admin_mcp.core.exceptions import RateLimitError

P = ParamSpec("P")
R = TypeVar("R")


class _Bucket:
    """Sliding-window counter. Not thread-safe; lives on the event loop."""

    __slots__ = ("_calls", "_lock", "max_calls", "window_seconds")

    def __init__(self, *, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> None:
        async with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            while self._calls and self._calls[0] < cutoff:
                self._calls.popleft()
            if len(self._calls) >= self.max_calls:
                retry_in = self.window_seconds - (now - self._calls[0])
                raise RateLimitError(
                    f"rate limit hit for {key!r}: "
                    f"max {self.max_calls}/{self.window_seconds:.0f}s, "
                    f"retry in ~{retry_in:.0f}s"
                )
            self._calls.append(now)


_buckets: dict[str, _Bucket] = {}


def rate_limited(
    *,
    key: str,
    max_per_hour: int,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorator limiting calls per hour per ``key``.

    Example::

        @rate_limited(key="company_create_post", max_per_hour=10)
        async def company_create_post(...): ...
    """

    bucket = _buckets.setdefault(key, _Bucket(max_calls=max_per_hour, window_seconds=3600.0))

    def decorator(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            await bucket.acquire(key)
            return await fn(*args, **kwargs)

        return wrapper

    return decorator


def reset_buckets_for_tests() -> None:
    """Clear all counters. Tests call this in fixtures to avoid bleed-through."""
    _buckets.clear()
