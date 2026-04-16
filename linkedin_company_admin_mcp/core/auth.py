"""Session management - login flow, status check, logout.

We never touch passwords. ``run_login`` opens a visible Chromium window
for the user to authenticate themselves; the persistent profile captures
the session. ``run_logout`` simply wipes the profile directory.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from linkedin_company_admin_mcp.config.schema import BrowserConfig
from linkedin_company_admin_mcp.constants import LINKEDIN_FEED_URL, LINKEDIN_LOGIN_URL
from linkedin_company_admin_mcp.core.browser import BrowserManager

_log = logging.getLogger(__name__)

_LOGIN_TIMEOUT_SECONDS = 300  # 5 minutes for the user to finish login + 2FA


@dataclass(slots=True)
class SessionInfo:
    """Snapshot of session state, safe to serialise to JSON."""

    logged_in: bool
    profile_dir: str
    profile_exists: bool
    note: str = ""


def check_status(config: BrowserConfig) -> SessionInfo:
    """Synchronous, fast - does not launch the browser."""
    profile = config.user_data_dir
    exists = profile.exists() and any(profile.iterdir()) if profile.exists() else False
    return SessionInfo(
        logged_in=exists,
        profile_dir=str(profile),
        profile_exists=exists,
        note="Profile directory is present, but cookie validity requires a live check."
        if exists
        else "No profile found. Run with --login to sign in.",
    )


async def run_login(config: BrowserConfig) -> SessionInfo:
    """Open a visible browser, wait for the user to complete login."""
    visible_config = BrowserConfig(
        headless=False,
        user_data_dir=config.user_data_dir,
        viewport_width=config.viewport_width,
        viewport_height=config.viewport_height,
        slow_mo_ms=config.slow_mo_ms,
    )
    async with BrowserManager(visible_config) as browser:
        pages = browser._context.pages if browser._context else []
        page = pages[0] if pages else await browser._context.new_page()  # type: ignore[union-attr]
        _log.info("opening login page; finish sign-in in the browser window")
        await page.goto(LINKEDIN_LOGIN_URL)
        try:
            await page.wait_for_url(
                f"{LINKEDIN_FEED_URL}**",
                timeout=_LOGIN_TIMEOUT_SECONDS * 1000,
            )
        except Exception as e:
            _log.error("login did not complete in time: %s", e)
            return SessionInfo(
                logged_in=False,
                profile_dir=str(config.user_data_dir),
                profile_exists=config.user_data_dir.exists(),
                note="Timed out waiting for /feed/ redirect.",
            )
    return SessionInfo(
        logged_in=True,
        profile_dir=str(config.user_data_dir),
        profile_exists=True,
        note="Login successful. Session cookies persisted.",
    )


def run_logout(config: BrowserConfig) -> SessionInfo:
    """Wipe the profile directory. Forces re-login on next start."""
    profile = config.user_data_dir
    if profile.exists():
        _remove_tree(profile)
        _log.info("profile wiped: %s", profile)
    return SessionInfo(
        logged_in=False,
        profile_dir=str(profile),
        profile_exists=False,
        note="Profile removed.",
    )


def _remove_tree(path: Path) -> None:
    """``shutil.rmtree`` but robust against read-only files on Windows."""

    def _on_rm_error(_func: object, path_str: str, _exc_info: object) -> None:
        _log.warning("could not remove %s", path_str)

    shutil.rmtree(path, onerror=_on_rm_error)
