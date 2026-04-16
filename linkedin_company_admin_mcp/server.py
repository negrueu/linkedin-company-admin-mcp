"""FastMCP server factory.

``create_mcp_server`` returns a fully wired ``FastMCP`` instance with every
tool group registered. The browser is started lazily on the first tool call
through a module-level singleton to avoid the cost (and login prompt) when
the user only asks for ``list_tools``.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from linkedin_company_admin_mcp import __version__
from linkedin_company_admin_mcp.config.schema import AppConfig
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.tools.company_admin import register_company_admin_tools
from linkedin_company_admin_mcp.tools.company_read import register_company_read_tools
from linkedin_company_admin_mcp.tools.session import register_session_tools

_log = logging.getLogger(__name__)

_browser_singleton: BrowserManager | None = None


def get_browser() -> BrowserManager:
    """Return the process-wide BrowserManager.

    Raises if ``create_mcp_server`` was never called.
    """
    if _browser_singleton is None:
        raise RuntimeError(
            "Browser manager not initialised. "
            "Did you call create_mcp_server() before tool execution?"
        )
    return _browser_singleton


def create_mcp_server(config: AppConfig) -> FastMCP[None]:
    """Build a FastMCP server configured against ``config``."""
    global _browser_singleton
    _browser_singleton = BrowserManager(config.browser)

    @asynccontextmanager
    async def lifespan(_server: FastMCP[None]) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if _browser_singleton is not None and _browser_singleton.is_started:
                _log.info("shutting down browser")
                await _browser_singleton.close()

    mcp: FastMCP[None] = FastMCP(
        name="linkedin-company-admin-mcp",
        version=__version__,
        instructions=(
            "LinkedIn Company Page administration. Read page analytics, "
            "manage posts, edit page details, grow followers, and bridge "
            "your personal profile for employee advocacy workflows."
        ),
        lifespan=lifespan,
    )

    register_session_tools(mcp, config=config, get_browser=get_browser)
    register_company_read_tools(mcp, get_browser=get_browser)
    register_company_admin_tools(mcp, get_browser=get_browser)

    return mcp
