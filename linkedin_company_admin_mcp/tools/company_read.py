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
    COMPANY_ADMIN_ANALYTICS_FOLLOWERS,
    COMPANY_ADMIN_ANALYTICS_UPDATES,
    COMPANY_ADMIN_EDIT_MODAL,
    COMPANY_ADMIN_MANAGE_ADMINS,
    COMPANY_ADMIN_NOTIFICATIONS,
    COMPANY_ADMIN_PAGE_POSTS,
)

GetBrowser = Callable[[], BrowserManager]


# --- JS snippets -----------------------------------------------------------

# Reads every form field from the "Edit Page" modal, which is the only
# admin-facing place that renders all structured fields (name, tagline,
# description, website, industry, size, type, phone, founded year).
#
# Also captures followers count and slug from the dashboard chrome behind
# the modal. The modal itself is triggered by ?editPage=true in the URL;
# no button click needed.
_JS_READ_PAGE = r"""
async () => {
    const dlg = document.querySelector('[role="dialog"]');
    if (!dlg) return { ok: false, note: "Edit Page modal did not open. Retry via company_read_page." };

    // Field readers. Select/typeahead values come back as raw IDs or codes;
    // for select we also include the visible option text.
    const val = (sel) => {
        const el = dlg.querySelector(sel);
        if (!el) return null;
        return (el.value ?? el.textContent ?? "").toString().trim() || null;
    };
    const sel = (id) => {
        const el = dlg.querySelector(id);
        if (!el || el.tagName !== "SELECT") return null;
        const opt = el.options[el.selectedIndex];
        return {
            value: (el.value || "").trim() || null,
            text: opt ? (opt.textContent || "").trim() || null : null,
        };
    };

    // Ensure we visit the Details tab once so its fields become readable.
    const btns = Array.from(dlg.querySelectorAll('button'));
    const detailsBtn = btns.find((b) => /^\s*details\s*$/i.test(b.textContent || ""));
    if (detailsBtn && detailsBtn.getAttribute("aria-selected") !== "true") {
        detailsBtn.click();
        await new Promise((r) => setTimeout(r, 1000));
    }

    const pageInfo = {
        name: val("#organization-name-field"),
        slug: val("#organization-public-url-field"),
        tagline: val("#organization-tagline-field"),
        description: val("#organization-description-field"),
        website: val("#organization-website-field"),
    };
    const details = {
        industry: val("#organization-industry-typeahead"),
        size: sel("#organization-size-select"),
        type: sel("#organization-type-select"),
        phone: val("#organization-phone-field"),
        founded_year: val("#organization-founded-on-input"),
    };

    // Followers live on the dashboard chrome behind the modal.
    const followerLink = document.querySelector(
        "a.org-organizational-page-admin-navigation__follower-count"
    );
    const followerText = followerLink ? (followerLink.textContent || "").trim() : null;
    const followerMatch = followerText ? followerText.match(/([0-9][0-9,.]*)\s+follower/i) : null;

    return {
        ok: true,
        name: pageInfo.name,
        slug: pageInfo.slug,
        public_url: pageInfo.slug ? `https://www.linkedin.com/company/${pageInfo.slug}/` : null,
        tagline: pageInfo.tagline,
        description: pageInfo.description,
        website: pageInfo.website,
        industry: details.industry,
        company_size: details.size,
        company_type: details.type,
        phone: details.phone,
        founded_year: details.founded_year,
        followers_text: followerText,
        followers_count: followerMatch ? Number(followerMatch[1].replace(/[,.]/g, "")) : null,
    };
}
"""

_JS_LIST_POSTS = r"""
async (limit) => {
    for (let i = 0; i < 3; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise((r) => setTimeout(r, 800));
    }
    const nodes = Array.from(
        document.querySelectorAll('[data-urn^="urn:li:activity"]')
    );
    return nodes.slice(0, limit).map((node) => {
        const urn = node.getAttribute('data-urn');
        const text = (node.querySelector('div[dir="ltr"]') || {}).innerText || '';
        const time = (node.querySelector('time') || {}).getAttribute?.('datetime') || null;
        const reactions = (
            node.querySelector('button[aria-label*="reaction" i], span[aria-label*="like" i]')
            || {}
        ).getAttribute?.('aria-label') || null;
        const comments = (
            node.querySelector('button[aria-label*="comment" i]')
            || {}
        ).getAttribute?.('aria-label') || null;
        return { urn, text: text.slice(0, 1000), time, reactions, comments };
    });
}
"""

_JS_LIST_FOLLOWERS = r"""
async (limit) => {
    for (let i = 0; i < 4; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise((r) => setTimeout(r, 800));
    }
    const items = Array.from(
        document.querySelectorAll('.org-view-page-followers-module__follower-list-item')
    );
    return items.slice(0, limit).map((li) => {
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
async (limit) => {
    await new Promise((r) => setTimeout(r, 1500));
    const empty = document.querySelector(
        '.nt-empty-state, [aria-label*="No notifications" i]'
    );
    if (empty) return { empty: true, items: [] };
    const cards = Array.from(
        document.querySelectorAll('[data-urn*="notification"], li.nt-card')
    );
    return {
        empty: cards.length === 0,
        items: cards.slice(0, limit).map((card) => ({
            text: (card.innerText || '').slice(0, 500).trim(),
            link: (card.querySelector('a[href]') || {}).href || null,
        })),
    };
}
"""

# Admin rows use tr.org-admin-roles-module__row. Name + headline live in
# artdeco-entity-lockup; role uses p.label-20dp (or the legacy class).
_JS_LIST_ADMINS = r"""
() => {
    const rows = Array.from(
        document.querySelectorAll(
            'tr.org-admin-roles-module__row, .org-admin-roles-module__row'
        )
    );
    return rows.map((row) => {
        const nameEl = row.querySelector('.artdeco-entity-lockup__title');
        const headlineEl = row.querySelector('.artdeco-entity-lockup__subtitle');
        const linkEl = row.querySelector('a[href*="/in/"]');
        const roleEl = row.querySelector(
            'p.label-20dp, .org-admin-roles-module__role'
        );
        const href = linkEl ? linkEl.getAttribute('href') : null;
        return {
            name: nameEl ? (nameEl.innerText || nameEl.textContent || '').trim() || null : null,
            headline: headlineEl
                ? (headlineEl.innerText || headlineEl.textContent || '').trim() || null
                : null,
            profile_url: href
                ? (href.startsWith('http') ? href : `https://www.linkedin.com${href}`)
                : null,
            role: roleEl ? (roleEl.innerText || roleEl.textContent || '').trim() || null : null,
        };
    });
}
"""

# Analytics: each metric renders inside a member-analytics-addon-card.
# Inside, a numeric value and a label sit as siblings; we extract both
# as text so LinkedIn's localisation doesn't trip us up.
_JS_READ_ANALYTICS = r"""
async () => {
    await new Promise((r) => setTimeout(r, 1200));
    const cards = Array.from(
        document.querySelectorAll(
            '.member-analytics-addon-card__base-card, .member-analytics-addon-metrics-carousel-item'
        )
    );
    const metrics = cards.map((card) => {
        const text = (card.innerText || '').trim();
        const lines = text.split('\n').map((s) => s.trim()).filter(Boolean);
        return {
            raw: text.slice(0, 400),
            lines,
            value: lines[0] || null,
            label: lines[1] || null,
        };
    });
    const rangeBtn = document.querySelector('button[aria-label^="Date range"]');
    const range = rangeBtn ? (rangeBtn.getAttribute('aria-label') || null) : null;
    return { metrics, date_range: range };
}
"""


def register_company_read_tools(mcp: FastMCP[None], *, get_browser: GetBrowser) -> None:
    """Attach the 6 read-only Company Page tools to ``mcp``."""

    @mcp.tool(
        title="Read company page",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read"},
    )
    async def company_read_page(
        company_id: str,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """Read every structured field for a company page.

        Uses LinkedIn's ``?editPage=true`` admin modal - the only place
        that exposes name, tagline, description, website, industry, size,
        type, phone and founded year all at once. The modal closes on
        navigation away; no state is modified.

        Args:
            company_id: Numeric page ID (e.g. ``"106949933"``) or a full
                ``linkedin.com/company/...`` URL.

        Returns:
            ``{name, slug, public_url, tagline, description, website,
            industry, company_size, company_type, phone, founded_year,
            followers_text, followers_count, company_id, admin_url}``.
        """
        try:
            del ctx  # not used
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_EDIT_MODAL.format(company_id=cid))
            await page.wait_for_selector('[role="dialog"]', timeout=15_000)
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
    async def company_list_posts(
        company_id: str,
        max_posts: int = 20,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """List posts published by the company page.

        Args:
            company_id: Numeric page ID or URL.
            max_posts: Cap on returned posts (1-100, default 20).

        Returns:
            ``{company_id, count, posts: [{urn, text, time, reactions, comments}]}``.
        """
        try:
            del ctx
            max_posts = max(1, min(100, max_posts))
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_PAGE_POSTS.format(company_id=cid))
            posts: list[dict[str, object]] = await page.evaluate(_JS_LIST_POSTS, max_posts)
            return {"company_id": cid, "count": len(posts), "posts": posts}
        except Exception as e:
            raise_tool_error(e, "company_list_posts")

    @mcp.tool(
        title="List company followers",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "followers"},
    )
    async def company_list_followers(
        company_id: str,
        max_results: int = 50,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """List followers of the company page.

        Args:
            company_id: Numeric page ID or URL.
            max_results: Cap on returned followers (1-200, default 50).
        """
        try:
            del ctx
            max_results = max(1, min(200, max_results))
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_ANALYTICS_FOLLOWERS.format(company_id=cid))
            followers: list[dict[str, object]] = await page.evaluate(
                _JS_LIST_FOLLOWERS, max_results
            )
            return {"company_id": cid, "count": len(followers), "followers": followers}
        except Exception as e:
            raise_tool_error(e, "company_list_followers")

    @mcp.tool(
        title="List company mentions / notifications",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "mentions"},
    )
    async def company_list_mentions(
        company_id: str,
        max_results: int = 20,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """List admin notifications for the page."""
        try:
            del ctx
            max_results = max(1, min(100, max_results))
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_NOTIFICATIONS.format(company_id=cid))
            data: dict[str, object] = await page.evaluate(_JS_LIST_MENTIONS, max_results)
            data["company_id"] = cid
            return data
        except Exception as e:
            raise_tool_error(e, "company_list_mentions")

    @mcp.tool(
        title="List company admins",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"company", "read", "admin"},
    )
    async def company_manage_admins(
        company_id: str,
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """List current admins of the page."""
        try:
            del ctx
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto(COMPANY_ADMIN_MANAGE_ADMINS.format(company_id=cid))
            await page.wait_for_timeout(1500)
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
        scope: str = "updates",
        ctx: Context | None = None,
    ) -> dict[str, object]:
        """Read metric cards from the analytics page.

        Args:
            company_id: Numeric page ID or URL.
            scope: ``"updates"`` (post performance), ``"followers"``
                (audience growth), or ``"all"`` (both).

        Returns:
            ``{company_id, scope, <scope>: {metrics, date_range}}``
            where each metric is ``{raw, lines, value, label}``.
        """
        try:
            del ctx
            if scope not in {"updates", "followers", "all"}:
                raise ValueError(f"Invalid scope {scope!r}; expected updates|followers|all")
            cid = normalise_company_id(company_id)
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()

            async def _fetch(scope_name: str) -> dict[str, object]:
                url = (
                    COMPANY_ADMIN_ANALYTICS_UPDATES
                    if scope_name == "updates"
                    else COMPANY_ADMIN_ANALYTICS_FOLLOWERS
                )
                await page.goto(url.format(company_id=cid))
                await page.wait_for_timeout(2500)
                data: dict[str, object] = await page.evaluate(_JS_READ_ANALYTICS)
                return data

            result: dict[str, object] = {"company_id": cid, "scope": scope}
            if scope in ("updates", "all"):
                result["updates"] = await _fetch("updates")
            if scope in ("followers", "all"):
                result["followers"] = await _fetch("followers")
            return result
        except Exception as e:
            raise_tool_error(e, "company_analytics")


__all__ = ["register_company_read_tools"]
