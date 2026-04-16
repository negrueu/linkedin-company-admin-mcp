"""Company Page administrative writes (non-content).

These tools edit page metadata, not posts: About / Logo / Details.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict

from fastmcp import Context, FastMCP

from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.core.rate_limit import rate_limited
from linkedin_company_admin_mcp.error_handler import raise_tool_error
from linkedin_company_admin_mcp.providers.base import (
    AdminProvider,
    EditAboutRequest,
    EditLogoRequest,
    UpdateDetailsRequest,
)
from linkedin_company_admin_mcp.providers.browser_provider import BrowserAdminProvider

GetBrowser = Callable[[], BrowserManager]


def _make_provider(get_browser: GetBrowser) -> AdminProvider:
    return BrowserAdminProvider(get_browser())


def register_company_admin_tools(
    mcp: FastMCP[None],
    *,
    get_browser: GetBrowser,
) -> None:
    """Attach 3 admin write tools."""

    @mcp.tool(
        title="Edit company About",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "admin"},
    )
    @rate_limited(key="company_edit_about", max_per_hour=20)
    async def company_edit_about(
        company_id: str,
        about_text: str,
        ctx: Context,
    ) -> dict[str, object]:
        """Replace the company page About section.

        Args:
            company_id: Numeric page ID or full LinkedIn URL.
            about_text: The new description. LinkedIn limits this to
                ~2000 characters. Line breaks are preserved.

        Returns:
            ``{ok: True, detail: str}`` on success.
        """
        try:
            browser = get_browser()
            await browser.start()
            provider = BrowserAdminProvider(browser)
            result = await provider.edit_about(
                EditAboutRequest(company_id=company_id, about_text=about_text)
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_edit_about")

    @mcp.tool(
        title="Edit company logo / banner",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "admin"},
    )
    @rate_limited(key="company_edit_logo", max_per_hour=10)
    async def company_edit_logo(
        company_id: str,
        ctx: Context,
        logo_path: str | None = None,
        banner_path: str | None = None,
    ) -> dict[str, object]:
        """Upload a new logo and/or banner image for the page.

        Args:
            company_id: Numeric page ID or URL.
            logo_path: Absolute path to the logo file (PNG/JPG, square
                recommended, minimum 300x300).
            banner_path: Absolute path to the banner file (PNG/JPG,
                1128x191 recommended).

        At least one of ``logo_path`` / ``banner_path`` must be provided.
        """
        try:
            if not logo_path and not banner_path:
                return {
                    "ok": False,
                    "detail": "At least one of logo_path or banner_path is required.",
                }
            browser = get_browser()
            await browser.start()
            provider = BrowserAdminProvider(browser)
            result = await provider.edit_logo(
                EditLogoRequest(
                    company_id=company_id,
                    logo_path=logo_path,
                    banner_path=banner_path,
                )
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_edit_logo")

    @mcp.tool(
        title="Update company details",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "admin"},
    )
    @rate_limited(key="company_update_details", max_per_hour=20)
    async def company_update_details(
        company_id: str,
        ctx: Context,
        website: str | None = None,
        industry: str | None = None,
        size_range: str | None = None,
        specialties: list[str] | None = None,
    ) -> dict[str, object]:
        """Update the page's website, industry, size bracket or specialties.

        All arguments are optional; supply only the fields you want to
        change. Fields not passed are left as-is on LinkedIn.

        Args:
            company_id: Numeric page ID or URL.
            website: Public URL for the company (e.g. ``"https://ketu.ai"``).
            industry: Free-form industry name (must match a LinkedIn value
                such as ``"Information Technology"`` - the dropdown auto-completes).
            size_range: LinkedIn's size bracket label, e.g.
                ``"2-10 employees"``, ``"11-50 employees"``.
            specialties: List of specialty strings, joined with commas.
        """
        try:
            browser = get_browser()
            await browser.start()
            provider = BrowserAdminProvider(browser)
            result = await provider.update_details(
                UpdateDetailsRequest(
                    company_id=company_id,
                    website=website,
                    industry=industry,
                    size_range=size_range,
                    specialties=specialties,
                )
            )
            return asdict(result)
        except Exception as e:
            raise_tool_error(e, "company_update_details")


__all__ = ["register_company_admin_tools"]
