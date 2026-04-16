"""Read-only tools for LinkedIn Company Pages.

Each tool:
    1. Navigates to the relevant admin URL.
    2. Waits for the network to settle.
    3. Extracts structured data via ``page.evaluate`` (runs in the browser,
       avoiding the need to round-trip full HTML back to Python).

JavaScript snippets live inline as string constants at the top so they can
be reviewed alongside the Python wrapper. Every tool is decorated with
``readOnlyHint`` so LinkedIn admin-side write operations never happen
during these calls.
"""

from __future__ import annotations

from collections.abc import Callable

from fastmcp import Context, FastMCP

from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.core.utils import normalise_company_id
from linkedin_company_admin_mcp.error_handler import raise_tool_error
from linkedin_company_admin_mcp.selectors import (
    COMPANY_ADMIN_DASHBOARD,
    COMPANY_ADMIN_FOLLOWERS,
    COMPANY_ADMIN_MANAGE_ADMINS,
    COMPANY_ADMIN_NOTIFICATIONS,
    COMPANY_ADMIN_PAGE_POSTS,
)

GetBrowser = Callable[[], BrowserManager]


# --- JS snippets -----------------------------------------------------------

_JS_READ_PAGE = r"""
() => {
    const h1 = document.querySelector('h1');
    const followersLink = document.querySelector('a[href*="/followers/"]');
    const tagline = document.querySelector(
        'p.org-top-card-summary__tagline, .org-top-card-summary__tagline'
    );
    return {
        name: h1 ? h1.innerText.trim() : null,
        followersText: followersLink ? followersLink.innerText.trim() : null,
        tagline: tagline ? tagline.innerText.trim() : null,
        bodyText: document.body.innerText.slice(0, 2000),
    };
}
"""

_JS_LIST_POSTS = r"""
async () => {
    // Scroll to pull more posts into the DOM.
    for (let i = 0; i < 3; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise((r) => setTimeout(r, 800));
    }
    const nodes = Array.from(
        document.querySelectorAll('[data-urn^="urn:li:activity"]')
    );
    return nodes.slice(0, 50).map((node) => {
        const urn = node.getAttribute('data-urn');
        const text = (node.querySelector('div[dir="ltr"]') || {}).innerText || '';
        const time = (node.querySelector('time') || {}).getAttribute?.('datetime') || null;
        const reactions = (
            node.querySelector('button[aria-label*="reaction"], span[aria-label*="like"]')
            || {}
        ).getAttribute?.('aria-label') || null;
        return { urn, text: text.slice(0, 1000), time, reactions };
    });
}
"""

_JS_LIST_FOLLOWERS = r"""
async () => {
    for (let i = 0; i < 4; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise((r) => setTimeout(r, 800));
    }
    const items = Array.from(
        document.querySelectorAll('.org-view-page-followers-module__follower-list-item')
    );
    return items.slice(0, 100).map((li) => {
        const name = (li.querySelector('.artdeco-entity-lockup__title') || {}).innerText || null;
        const headline = (
            li.querySelector(
                '.artdeco-entity-lockup__subtitle, .artdeco-entity-lockup__caption'
            ) || {}
        ).innerText || null;
        const href = (li.querySelector('a[href*="/in/"]') || {}).href || null;
        return {
            name: name && name.trim(),
            headline: headline && headline.trim(),
            profile_url: href,
        };
    });
}
"""

_JS_LIST_MENTIONS = r"""
async () => {
    await new Promise((r) => setTimeout(r, 1500));
    const empty = document.querySelector(
        '.nt-empty-state, [aria-label*="No notifications"]'
    );
    if (empty) return { empty: true, items: [] };
    const cards = Array.from(
        document.querySelectorAll('[data-urn*="notification"], li.nt-card')
    );
    return {
        empty: cards.length === 0,
        items: cards.slice(0, 50).map((card) => ({
            text: (card.innerText || '').slice(0, 500).trim(),
            link: (card.querySelector('a[href]') || {}).href || null,
        })),
    };
}
"""

_JS_LIST_ADMINS = r"""
() => {
    const rows = Array.from(
        document.querySelectorAll(
            '.org-admin-roles-module__table-wrapper tbody tr'
        )
    );
    return rows.map((row) => {
        const nameAnchor = row.querySelector('a[href*="/in/"]');
        const roleEl = row.querySelector('.org-admin-roles-module__role');
        const headline = row.querySelector('.entity-headline');
        return {
            name: nameAnchor ? nameAnchor.innerText.trim() : null,
            profile_url: nameAnchor ? nameAnchor.href : null,
            role: roleEl ? roleEl.innerText.trim() : null,
            headline: headline ? headline.innerText.trim() : null,
        };
    });
}
"""

_JS_READ_ANALYTICS = r"""
() => {
    // Analytics pages display metrics in .org-analytics-*-card.
    // We capture all numeric cards plus body text as fallback.
    const cards = Array.from(
        document.querySelectorAll(
            '[class*="analytics"] [class*="metric"], [class*="analytics"] .artdeco-card'
        )
    ).slice(0, 12);
    return {
        metrics: cards.map((c) => (c.innerText || '').trim().slice(0, 200)),
        bodyText: document.body.innerText.slice(0, 3000),
    };
}
"""


def register_company_read_tools(mcp: FastMCP[None], *, get_browser: GetBrowser) -> None:
    """Attach the 6 read-only Company Page tools to ``mcp``."""

    @mcp.tool(
        title="Read company page",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read"},
    )
    async def company_read_page(company_id: str, ctx: Context) -> dict[str, object]:
        """Fetch the admin dashboard summary for a company page.

        Args:
            company_id: Numeric page ID (e.g. ``"106949933"``) or a full
                ``linkedin.com/company/...`` URL.

        Returns:
            A dict with ``name``, ``tagline``, ``followers_text`` (raw) and
            the first 2000 chars of the dashboard body for diagnostics.
        """
        try:
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_DASHBOARD.format(company_id=cid))
            data: dict[str, object] = await page.evaluate(_JS_READ_PAGE)
            data["company_id"] = cid
            data["admin_url"] = page.url
            return data
        except Exception as e:
            raise_tool_error(e, "company_read_page")

    @mcp.tool(
        title="List company posts",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "posts"},
    )
    async def company_list_posts(company_id: str, ctx: Context) -> dict[str, object]:
        """List posts published by the company page (up to 50 most recent).

        Each post contains ``urn``, ``text`` (first 1000 chars), ``time``
        (ISO 8601), and a raw ``reactions`` label (e.g. ``"3 likes"``).
        """
        try:
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_PAGE_POSTS.format(company_id=cid))
            posts: list[dict[str, object]] = await page.evaluate(_JS_LIST_POSTS)
            return {"company_id": cid, "count": len(posts), "posts": posts}
        except Exception as e:
            raise_tool_error(e, "company_list_posts")

    @mcp.tool(
        title="List company followers",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "followers"},
    )
    async def company_list_followers(company_id: str, ctx: Context) -> dict[str, object]:
        """List followers of the company page (up to 100 most recent).

        Useful for community outreach. Returns ``name``, ``headline`` and
        ``profile_url`` per follower.
        """
        try:
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_FOLLOWERS.format(company_id=cid))
            followers: list[dict[str, object]] = await page.evaluate(_JS_LIST_FOLLOWERS)
            return {"company_id": cid, "count": len(followers), "followers": followers}
        except Exception as e:
            raise_tool_error(e, "company_list_followers")

    @mcp.tool(
        title="List company mentions / notifications",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "mentions"},
    )
    async def company_list_mentions(company_id: str, ctx: Context) -> dict[str, object]:
        """List admin notifications for the page (mentions, new followers,
        post engagement). Returns ``empty`` true when none exist.
        """
        try:
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_NOTIFICATIONS.format(company_id=cid))
            data: dict[str, object] = await page.evaluate(_JS_LIST_MENTIONS)
            data["company_id"] = cid
            return data
        except Exception as e:
            raise_tool_error(e, "company_list_mentions")

    @mcp.tool(
        title="List company admins",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "admin"},
    )
    async def company_manage_admins(company_id: str, ctx: Context) -> dict[str, object]:
        """List current admins of the page, their roles and profile URLs.

        Read-only in this release. Adding/removing admins happens through a
        flow that requires write confirmation; that will be a separate tool.
        """
        try:
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_MANAGE_ADMINS.format(company_id=cid))
            admins: list[dict[str, object]] = await page.evaluate(_JS_LIST_ADMINS)
            return {"company_id": cid, "count": len(admins), "admins": admins}
        except Exception as e:
            raise_tool_error(e, "company_manage_admins")

    @mcp.tool(
        title="Company analytics",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "analytics"},
    )
    async def company_analytics(
        company_id: str,
        ctx: Context,
        scope: str = "updates",
    ) -> dict[str, object]:
        """Capture the raw metrics block from the analytics page.

        Args:
            company_id: Numeric page ID or URL.
            scope: Which analytics page to read. One of: ``"updates"``
                (post performance), ``"followers"`` (audience growth),
                or ``"all"`` (captures both in sequence).

        Returns:
            A dict keyed by scope, each containing ``metrics`` (list of
            text blocks) and ``body_text`` (first 3000 chars of the
            rendered page for diagnostics).
        """
        try:
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()

            async def _fetch(scope_name: str) -> dict[str, object]:
                if scope_name == "updates":
                    url = f"https://www.linkedin.com/company/{cid}/admin/analytics/updates/"
                elif scope_name == "followers":
                    url = f"https://www.linkedin.com/company/{cid}/admin/analytics/followers/"
                else:
                    raise ValueError(f"unknown analytics scope: {scope_name!r}")
                await page.goto(url)
                data: dict[str, object] = await page.evaluate(_JS_READ_ANALYTICS)
                return data

            if scope in ("updates", "followers"):
                return {"company_id": cid, "scope": scope, scope: await _fetch(scope)}
            if scope == "all":
                return {
                    "company_id": cid,
                    "scope": "all",
                    "updates": await _fetch("updates"),
                    "followers": await _fetch("followers"),
                }
            raise ValueError(f"scope must be 'updates', 'followers' or 'all'; got {scope!r}")
        except Exception as e:
            raise_tool_error(e, "company_analytics")
