"""Package-wide constants."""

from __future__ import annotations

LINKEDIN_BASE_URL = "https://www.linkedin.com"
LINKEDIN_FEED_URL = f"{LINKEDIN_BASE_URL}/feed/"
LINKEDIN_LOGIN_URL = f"{LINKEDIN_BASE_URL}/login"

SESSION_WARMUP_DELAY_SECONDS = 3.0
DEFAULT_NAV_TIMEOUT_MS = 15_000
DEFAULT_TOOL_TIMEOUT_SECONDS = 60

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)
