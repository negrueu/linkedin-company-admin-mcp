"""Small helpers used across engine and tool modules."""

from __future__ import annotations

import asyncio
import random
import re
from typing import TypeVar

T = TypeVar("T")

_LINKEDIN_URN_RE = re.compile(
    r"^urn:li:(activity|ugcPost|share|organization|organizationAcl|fsd_profile):"
    r"[0-9A-Za-z_-]+(?:,[0-9A-Za-z_-]+)?$"
)
_LINKEDIN_ACTIVITY_IN_URL_RE = re.compile(r"urn:li:(activity|ugcPost|share):([0-9]+)")


async def human_delay(min_s: float = 0.3, max_s: float = 0.8) -> None:
    """Sleep for a randomised interval to look more human.

    Playwright/Patchright won't be flagged just by this, but combined with
    stealth settings it reduces the chance of captcha.
    """
    await asyncio.sleep(random.uniform(min_s, max_s))


def is_valid_urn(value: str) -> bool:
    """True if ``value`` matches a LinkedIn URN we expect to handle."""
    return bool(_LINKEDIN_URN_RE.match(value))


def extract_activity_urn(source: str) -> str | None:
    """Extract the first ``urn:li:activity:...`` (or ugcPost/share) match.

    Useful when LinkedIn embeds the URN inside a ``data-urn`` attribute,
    a URL, or an anchor ``href``. Returns ``None`` when nothing matches.
    """
    match = _LINKEDIN_ACTIVITY_IN_URL_RE.search(source)
    if match is None:
        return None
    return f"urn:li:{match.group(1)}:{match.group(2)}"


def normalise_company_id(raw: str) -> str:
    """Return the numeric ID from either a raw ID or a full URL.

    >>> normalise_company_id("106949933")
    '106949933'
    >>> normalise_company_id("https://www.linkedin.com/company/106949933/admin/")
    '106949933'
    >>> normalise_company_id("https://www.linkedin.com/company/my-company/")
    'my-company'
    """
    if raw.isdigit():
        return raw
    match = re.search(r"/company/([^/]+)/?", raw)
    if match:
        return match.group(1)
    return raw
