"""Company Page growth tools: invite-to-follow + scheduled-post list."""

from __future__ import annotations

from collections.abc import Callable

from fastmcp import Context, FastMCP

from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.core.rate_limit import rate_limited
from linkedin_company_admin_mcp.core.utils import normalise_company_id
from linkedin_company_admin_mcp.error_handler import raise_tool_error
from linkedin_company_admin_mcp.providers.shared import (
    js_click_by_text,
    remove_blocking_modal_outlet,
)
from linkedin_company_admin_mcp.selectors import COMPANY_ADMIN_DASHBOARD

GetBrowser = Callable[[], BrowserManager]


_JS_LIST_SCHEDULED = r"""
async () => {
    for (let i = 0; i < 2; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise((r) => setTimeout(r, 600));
    }
    const cards = Array.from(document.querySelectorAll(
        '[data-urn^="urn:li:scheduledShare"], [data-urn*="scheduled"]'
    ));
    return cards.slice(0, 50).map((node) => {
        const urn = node.getAttribute('data-urn');
        const text = (node.querySelector('div[dir="ltr"]') || {}).innerText || '';
        const timeNode = node.querySelector('time, [class*="scheduled-time"]');
        return {
            urn,
            text: text.slice(0, 500),
            scheduled_at: timeNode ? (timeNode.getAttribute('datetime') || timeNode.innerText) : null,
        };
    });
}
"""


def register_company_growth_tools(mcp: FastMCP[None], *, get_browser: GetBrowser) -> None:
    """Attach the 2 growth tools."""

    @mcp.tool(
        title="Invite connections to follow",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "write", "growth"},
    )
    @rate_limited(key="company_invite_to_follow", max_per_hour=3)
    async def company_invite_to_follow(
        company_id: str,
        ctx: Context,
        max_invites: int = 50,
    ) -> dict[str, object]:
        """Send follow invitations to your 1st-degree connections.

        LinkedIn caps these at 250 invites per page per month. The tool
        sends up to ``max_invites`` before stopping; LinkedIn will return
        an error banner once the monthly quota is reached and the run
        stops gracefully.

        Args:
            company_id: Numeric page ID or URL.
            max_invites: Hard cap for this invocation. Defaults to 50 so
                casual runs don't burn through the monthly allowance.
        """
        try:
            if max_invites <= 0 or max_invites > 250:
                return {
                    "ok": False,
                    "detail": "max_invites must be between 1 and 250.",
                }
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(f"{COMPANY_ADMIN_DASHBOARD.format(company_id=cid)}?invite=true")
            await remove_blocking_modal_outlet(page)
            await page.wait_for_timeout(2000)

            sent: int = await page.evaluate(
                "(cap) => {"
                "  const buttons = Array.from("
                '    document.querySelectorAll(\'button[aria-label*="Invite"][aria-label*="follow" i]\')'
                "  );"
                "  let count = 0;"
                "  for (const btn of buttons) {"
                "    if (count >= cap) break;"
                "    if (btn.disabled) continue;"
                "    btn.click();"
                "    count += 1;"
                "  }"
                "  return count;"
                "}",
                max_invites,
            )
            await page.wait_for_timeout(500)
            submitted = await js_click_by_text(page, "body", "Send invitations")
            if not submitted:
                submitted = await js_click_by_text(page, "body", "Invite")
            await page.wait_for_timeout(1500)
            return {
                "ok": True,
                "detail": f"Selected {sent} connection(s) to invite.",
                "extra": {
                    "selected": sent,
                    "submit_dispatched": submitted,
                },
            }
        except Exception as e:
            raise_tool_error(e, "company_invite_to_follow")

    @mcp.tool(
        title="List scheduled company posts",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "schedule"},
    )
    async def company_list_scheduled(company_id: str, ctx: Context) -> dict[str, object]:
        """List posts queued for future publication (scheduled).

        Returns each scheduled post's URN, preview text (first 500 chars)
        and scheduled time (ISO when available, raw display string otherwise).
        """
        try:
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(f"https://www.linkedin.com/company/{cid}/admin/page-posts/scheduled/")
            await remove_blocking_modal_outlet(page)
            scheduled: list[dict[str, object]] = await page.evaluate(_JS_LIST_SCHEDULED)
            return {"company_id": cid, "count": len(scheduled), "posts": scheduled}
        except Exception as e:
            raise_tool_error(e, "company_list_scheduled")


__all__ = ["register_company_growth_tools"]
