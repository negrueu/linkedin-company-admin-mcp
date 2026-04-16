"""Persistent Patchright context manager.

We use a module-level singleton because LinkedIn does NOT tolerate parallel
operations on the same session - clicks interleave and state gets corrupted.
Tools that share browser state should be serialised at the server layer
(see ``server.create_mcp_server``).

The browser profile lives in the user's home directory by default
(``~/.linkedin-company-admin/profile``), chmod'd to ``0o700`` on Unix.
All cookies and localStorage are persisted automatically by Patchright's
``launch_persistent_context`` API - we do not manage cookies explicitly.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from linkedin_company_admin_mcp.config.schema import BrowserConfig
from linkedin_company_admin_mcp.constants import (
    DEFAULT_NAV_TIMEOUT_MS,
    LINKEDIN_FEED_URL,
    SESSION_WARMUP_DELAY_SECONDS,
    USER_AGENT,
)
from linkedin_company_admin_mcp.core.exceptions import AuthenticationError

if TYPE_CHECKING:
    from patchright.async_api import BrowserContext, Page, Playwright

_log = logging.getLogger(__name__)


def _secure_profile_dir(path: Path) -> None:
    """Create the profile directory and tighten permissions on Unix."""
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            path.chmod(0o700)
        except OSError as e:
            _log.warning("could not chmod %s to 0700: %s", path, e)


class BrowserManager:
    """Lifecycle owner for the Patchright Playwright + BrowserContext.

    Use via ``async with BrowserManager(config) as browser:`` or call
    ``start()`` / ``close()`` manually. ``get_page()`` returns a warmed-up
    page reused across calls.
    """

    def __init__(self, config: BrowserConfig) -> None:
        self._config = config
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._session_warmed_up = False

    @property
    def config(self) -> BrowserConfig:
        return self._config

    @property
    def is_started(self) -> bool:
        return self._context is not None

    async def start(self) -> None:
        """Launch Patchright and open the persistent context."""
        if self._context is not None:
            return
        from patchright.async_api import async_playwright

        _secure_profile_dir(self._config.user_data_dir)
        self._playwright = await async_playwright().start()
        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self._config.user_data_dir),
            headless=self._config.headless,
            viewport={
                "width": self._config.viewport_width,
                "height": self._config.viewport_height,
            },
            user_agent=USER_AGENT,
            slow_mo=self._config.slow_mo_ms,
            locale="en-US",
        )
        _log.info(
            "browser started (headless=%s, profile=%s)",
            self._config.headless,
            self._config.user_data_dir,
        )

    async def close(self) -> None:
        """Shut everything down in reverse order."""
        if self._context is not None:
            try:
                await self._context.close()
            except Exception as e:
                _log.warning("error closing context: %s", e)
            finally:
                self._context = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as e:
                _log.warning("error stopping playwright: %s", e)
            finally:
                self._playwright = None
        self._page = None
        self._session_warmed_up = False

    async def __aenter__(self) -> BrowserManager:
        await self.start()
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.close()

    async def get_page(self) -> Page:
        """Return a ready-to-use page. Warms up the session on first call.

        Warm-up: navigate to ``/feed/`` once after context launch. Without
        this, the first admin-dashboard navigation may hit an authwall
        because cookies haven't fully activated.
        """
        if self._context is None:
            raise RuntimeError("BrowserManager not started")
        if self._page is None:
            pages = self._context.pages
            self._page = pages[0] if pages else await self._context.new_page()
            self._page.set_default_navigation_timeout(DEFAULT_NAV_TIMEOUT_MS)
        if not self._session_warmed_up:
            await self._warm_up(self._page)
        return self._page

    async def _warm_up(self, page: Page) -> None:
        """Hit /feed/ and confirm the session is authenticated."""
        _log.debug("warming up session via %s", LINKEDIN_FEED_URL)
        await page.goto(LINKEDIN_FEED_URL, wait_until="domcontentloaded")
        await page.wait_for_timeout(int(SESSION_WARMUP_DELAY_SECONDS * 1000))
        if "/login" in page.url or "/authwall" in page.url:
            raise AuthenticationError(
                "Not logged in. Run `linkedin-company-admin-mcp --login` first."
            )
        self._session_warmed_up = True
        _log.info("session warmed up via /feed/")
