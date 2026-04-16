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
from linkedin_company_admin_mcp.selectors import (
    COMPANY_ADMIN_DASHBOARD,
    COMPANY_ADMIN_SCHEDULED_LIST,
)

GetBrowser = Callable[[], BrowserManager]


# Scheduled posts render inside a share-box-v2 modal over the admin page
# (no standalone URL, no data-urn). We use the preview button's aria-label
# to extract the scheduled datetime deterministically, e.g.:
#     "Preview of the scheduled post that will be published on
#      Fri April 17, 2026 at 6:00 AM, click to see detail view"
# Text body is the <li>'s trailing text line after the header row.
_JS_LIST_SCHEDULED = r"""
async () => {
    // Wait for the dialog to mount if a race left us early.
    for (let i = 0; i < 10; i++) {
        if (document.querySelector('li.share-post-list-view__item')) break;
        await new Promise(r => setTimeout(r, 500));
    }
    const rows = Array.from(document.querySelectorAll('li.share-post-list-view__item'));
    return rows.map((li, idx) => {
        const preview = li.querySelector('button');
        const aria = preview ? (preview.getAttribute('aria-label') || '') : '';
        const m = aria.match(/published on (.+?), click to see/i);
        const when = m ? m[1].trim() : null;
        const lines = (li.innerText || '').split('\n').map(s => s.trim()).filter(Boolean);
        // lines[0] = "Scheduled by <name>", lines[1] = "Posting <date>", lines[2+] = body
        const body = lines.slice(2).join('\n');
        return {
            index: idx,
            scheduled_at_display: when,
            scheduled_by: lines[0] ? lines[0].replace(/^Scheduled by /i, '') : null,
            text: body.slice(0, 500),
        };
    });
}
"""


_JS_CANCEL_SCHEDULED = r"""
async (index) => {
    const rows = Array.from(document.querySelectorAll('li.share-post-list-view__item'));
    if (index >= rows.length) return { phase: 'index-oob', count: rows.length };
    const trigger = rows[index].querySelector('button.share-post-action-bar__dropdown-trigger');
    if (!trigger) return { phase: 'trigger' };
    trigger.click();
    await new Promise(r => setTimeout(r, 1200));
    const dd = Array.from(document.querySelectorAll('.artdeco-dropdown__content--is-open'))
        .find(el => el.offsetParent !== null);
    if (!dd) return { phase: 'dropdown' };
    const clickables = Array.from(dd.querySelectorAll('button, [role="button"], a, .artdeco-dropdown__item'));
    const del = clickables.find(el => (el.innerText || el.textContent || '').trim().toLowerCase() === 'delete post');
    if (!del) return { phase: 'delete-item' };
    del.click();
    await new Promise(r => setTimeout(r, 2500));
    const confirm = Array.from(
        document.querySelectorAll('[role="alertdialog"] button, [role="dialog"] button')
    ).find(b => /^delete$/i.test((b.textContent || '').trim()) && !b.disabled && b.offsetParent !== null);
    if (!confirm) return { phase: 'confirm' };
    confirm.click();
    await new Promise(r => setTimeout(r, 2000));
    return { ok: true };
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
        title="List scheduled company posts (optional cancel)",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"company", "read", "schedule"},
    )
    async def company_list_scheduled(
        company_id: str,
        cancel_index: int | None = None,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """List posts queued for future publication, optionally cancel one.

        LinkedIn renders the company scheduled queue as a dialog over the
        admin page-posts screen (no dedicated URL, no exposed URN per row).
        The rows are identified by stable 0-based index and the display
        datetime parsed from each preview button's aria-label.

        Args:
            company_id: Numeric page ID or company URL.
            cancel_index: Optional 0-based index into the list. When set,
                the entry at that index is cancelled via "Delete post"
                before the updated list is returned. Omit for read-only.

        Returns:
            ``count`` and ``posts`` - each post has ``index``,
            ``scheduled_at_display``, ``scheduled_by`` and ``text``.
            If ``cancel_index`` was used, ``cancelled`` is the removed row.
        """
        try:
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(
                COMPANY_ADMIN_SCHEDULED_LIST.format(company_id=cid),
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            await page.wait_for_selector('[role="dialog"]', timeout=15_000)
            await page.wait_for_timeout(2500)

            posts: list[dict[str, object]] = await page.evaluate(_JS_LIST_SCHEDULED)
            cancelled: dict[str, object] | None = None
            if cancel_index is not None:
                if cancel_index < 0 or cancel_index >= len(posts):
                    return {
                        "ok": False,
                        "detail": f"cancel_index {cancel_index} out of range (0..{len(posts) - 1}).",
                        "count": len(posts),
                        "posts": posts,
                    }
                cancelled = posts[cancel_index]
                result = await page.evaluate(_JS_CANCEL_SCHEDULED, cancel_index)
                if not result.get("ok"):
                    return {
                        "ok": False,
                        "detail": f"Cancel failed at phase {result.get('phase')!r}.",
                        "count": len(posts),
                        "posts": posts,
                    }
                await page.wait_for_timeout(2500)
                posts = await page.evaluate(_JS_LIST_SCHEDULED)
            return {
                "ok": True,
                "company_id": cid,
                "count": len(posts),
                "posts": posts,
                "cancelled": cancelled,
            }
        except Exception as e:
            raise_tool_error(e, "company_list_scheduled")


__all__ = ["register_company_growth_tools"]
