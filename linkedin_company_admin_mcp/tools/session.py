"""Session management tools.

These are the only tools that don't talk to LinkedIn directly - they
inspect or manipulate the local browser profile. They run fast and never
require the browser to be fully warmed up.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

from fastmcp import Context, FastMCP

from linkedin_company_admin_mcp.config.schema import AppConfig
from linkedin_company_admin_mcp.core.auth import (
    SessionInfo,
    check_status,
    run_logout,
)
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.error_handler import raise_tool_error

GetBrowser = Callable[[], BrowserManager]


def register_session_tools(
    mcp: FastMCP[None],
    *,
    config: AppConfig,
    get_browser: GetBrowser,
) -> None:
    """Attach session tools to ``mcp``.

    ``get_browser`` is injected so the tools never import ``server`` at
    module import time (which would create a cycle).
    """

    @mcp.tool(
        title="Session status",
        annotations={"readOnlyHint": True, "openWorldHint": False},
        tags={"session"},
    )
    async def session_status(ctx: Context) -> dict[str, object]:
        """Report whether a persistent LinkedIn profile is present.

        This is a fast local check - it does NOT open the browser or hit
        LinkedIn. Useful to decide whether a ``--login`` step is required.
        """
        try:
            info: SessionInfo = check_status(config.browser)
            return asdict(info)
        except Exception as e:
            raise_tool_error(e, "session_status")

    @mcp.tool(
        title="Warm up browser session",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"session"},
    )
    async def session_warmup(ctx: Context) -> dict[str, object]:
        """Launch the browser, navigate to /feed/, confirm authentication.

        Call this after ``--login`` to verify the session works before
        running other tools. Returns the current LinkedIn URL and a
        success flag.
        """
        try:
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            return {
                "authenticated": True,
                "current_url": page.url,
            }
        except Exception as e:
            raise_tool_error(e, "session_warmup")

    @mcp.tool(
        title="Logout",
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "openWorldHint": False,
        },
        tags={"session"},
    )
    async def session_logout(ctx: Context) -> dict[str, object]:
        """Wipe the persistent browser profile. Forces re-login next run.

        The operation is local - it deletes the profile directory. It does
        not sign you out on LinkedIn's side (cookies remain valid until
        they expire on the server). Run ``--login`` to sign in again.
        """
        try:
            browser = get_browser()
            if browser.is_started:
                await browser.close()
            info = run_logout(config.browser)
            return asdict(info)
        except Exception as e:
            raise_tool_error(e, "session_logout")
