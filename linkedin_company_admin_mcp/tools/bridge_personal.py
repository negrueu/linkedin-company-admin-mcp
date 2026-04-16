"""Bridge tools: the small set of personal-profile operations that exist
purely to support Company Page workflows (employee advocacy).

Anything else about personal profiles is out of scope - use
``stickerdaniel/linkedin-mcp-server`` for that.
"""

from __future__ import annotations

import logging
import urllib.parse
from collections.abc import Callable

from fastmcp import Context, FastMCP

from linkedin_company_admin_mcp.constants import LINKEDIN_FEED_URL
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.core.exceptions import SelectorError
from linkedin_company_admin_mcp.core.rate_limit import rate_limited
from linkedin_company_admin_mcp.core.utils import (
    extract_activity_urn,
    is_valid_urn,
    normalise_company_id,
)
from linkedin_company_admin_mcp.error_handler import raise_tool_error
from linkedin_company_admin_mcp.providers.shared import (
    js_click_by_text,
    quill_insert_text,
    remove_blocking_modal_outlet,
)

_log = logging.getLogger(__name__)

GetBrowser = Callable[[], BrowserManager]

_COMPOSER_EDITOR = 'div.ql-editor, div[role="textbox"][contenteditable="true"]'
_COMPOSER_POST_BUTTON = 'button[aria-label="Post"], button.share-actions__primary-action'


async def _open_personal_composer(page: object) -> None:
    """Land on /feed/ and open the Start-a-post composer."""
    await page.goto(LINKEDIN_FEED_URL)  # type: ignore[attr-defined]
    await remove_blocking_modal_outlet(page)  # type: ignore[arg-type]
    opened = await js_click_by_text(page, "body", "Start a post")  # type: ignore[arg-type]
    if not opened:
        raise SelectorError("Could not locate 'Start a post' entry point on /feed/.")
    await page.wait_for_selector(_COMPOSER_EDITOR, timeout=10_000)  # type: ignore[attr-defined]


async def _insert_company_mention(page: object, company_name: str) -> None:
    """Type ``@<name>`` and click the first matching mention suggestion."""
    handle: str = f"@{company_name}"
    await page.keyboard.type(handle)  # type: ignore[attr-defined]
    await page.wait_for_timeout(1200)  # type: ignore[attr-defined]
    clicked = await js_click_by_text(page, '[role="listbox"], .mentions-typeahead', company_name)  # type: ignore[arg-type]
    if not clicked:
        raise SelectorError(f"Mention dropdown did not show a match for {company_name!r}.")


def register_bridge_personal_tools(mcp: FastMCP[None], *, get_browser: GetBrowser) -> None:
    """Attach the 4 bridge tools."""

    @mcp.tool(
        title="Tag company in personal post",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"personal", "write", "bridge"},
    )
    @rate_limited(key="personal_tag_company", max_per_hour=20)
    async def personal_tag_company(
        company_name: str,
        lead_text: str,
        trailing_text: str,
        ctx: Context,
    ) -> dict[str, object]:
        """Publish a personal post mentioning your company page.

        The post is assembled as ``<lead_text>@<company>[first match]<trailing_text>``.

        Args:
            company_name: Display name of the Company Page to tag, matching
                the suggestion in LinkedIn's mention dropdown.
            lead_text: Text to insert before the mention.
            trailing_text: Text to insert after the mention.
        """
        try:
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await _open_personal_composer(page)
            if lead_text:
                await quill_insert_text(page, _COMPOSER_EDITOR, lead_text + " ")
            await _insert_company_mention(page, company_name)
            if trailing_text:
                await quill_insert_text(page, _COMPOSER_EDITOR, " " + trailing_text)
            await page.click(_COMPOSER_POST_BUTTON)
            await page.wait_for_timeout(2500)
            return {
                "ok": True,
                "detail": "Personal post with company mention published.",
                "extra": {"company_name": company_name},
            }
        except Exception as e:
            raise_tool_error(e, "personal_tag_company")

    @mcp.tool(
        title="Reshare company post on personal profile",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"personal", "write", "bridge"},
    )
    @rate_limited(key="personal_reshare_company_post", max_per_hour=15)
    async def personal_reshare_company_post(
        source_post_urn: str,
        ctx: Context,
        thoughts_text: str | None = None,
    ) -> dict[str, object]:
        """Share a Company Page post onto the signed-in user's profile.

        Args:
            source_post_urn: URN of the company post (from
                ``company_list_posts``).
            thoughts_text: Optional commentary added above the reshared post.
        """
        try:
            if not is_valid_urn(source_post_urn):
                raise ValueError(f"Invalid source URN: {source_post_urn!r}")
            activity = extract_activity_urn(source_post_urn)
            if activity is None:
                raise ValueError(f"Cannot extract activity from {source_post_urn!r}")

            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            encoded = urllib.parse.quote(activity, safe="")
            await page.goto(f"{LINKEDIN_FEED_URL}update/{encoded}/")
            await remove_blocking_modal_outlet(page)
            await page.wait_for_timeout(1200)

            opened = await js_click_by_text(page, "body", "Repost")
            if not opened:
                opened = await js_click_by_text(page, "body", "Share")
            if not opened:
                raise SelectorError("Repost entry point not found on post.")
            clicked = await js_click_by_text(page, "body", "Repost with your thoughts")
            if not clicked:
                clicked = await js_click_by_text(page, "body", "Reshare with thoughts")
            if not clicked:
                raise SelectorError("'Repost with your thoughts' option missing.")
            await page.wait_for_selector(_COMPOSER_EDITOR, timeout=8_000)
            if thoughts_text:
                await quill_insert_text(page, _COMPOSER_EDITOR, thoughts_text)
            await page.click(_COMPOSER_POST_BUTTON)
            await page.wait_for_timeout(2000)
            return {
                "ok": True,
                "detail": "Company post reshared on personal profile.",
                "extra": {"source_urn": activity},
            }
        except Exception as e:
            raise_tool_error(e, "personal_reshare_company_post")

    @mcp.tool(
        title="Comment on company post as admin",
        annotations={"readOnlyHint": False, "openWorldHint": True},
        tags={"personal", "write", "bridge"},
    )
    @rate_limited(key="personal_comment_as_admin", max_per_hour=30)
    async def personal_comment_as_admin(
        company_id: str,
        source_post_urn: str,
        comment_text: str,
        ctx: Context,
        comment_as_company: bool = True,
    ) -> dict[str, object]:
        """Post a comment on a company post, optionally as the page itself.

        When ``comment_as_company`` is ``True`` (default) the tool flips
        the identity selector to the Company Page before submitting; when
        ``False`` the comment is posted as the signed-in personal account.

        Args:
            company_id: Numeric page ID or URL (used to locate the
                identity selector).
            source_post_urn: URN of the target post.
            comment_text: The comment body.
            comment_as_company: See above.
        """
        try:
            if not is_valid_urn(source_post_urn):
                raise ValueError(f"Invalid post URN: {source_post_urn!r}")
            activity = extract_activity_urn(source_post_urn)
            if activity is None:
                raise ValueError(f"Cannot extract activity from {source_post_urn!r}")

            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            encoded = urllib.parse.quote(activity, safe="")
            await page.goto(f"{LINKEDIN_FEED_URL}update/{encoded}/")
            await remove_blocking_modal_outlet(page)
            await page.wait_for_timeout(1500)

            comment_editor = 'div[role="textbox"][aria-label*="comment" i]'
            await page.wait_for_selector(comment_editor, timeout=10_000)

            if comment_as_company:
                identity_label = normalise_company_id(company_id)
                switched = await page.evaluate(
                    "([cid]) => {"
                    "  const btn = document.querySelector('button[aria-label*=\"Comment as\" i]');"
                    "  if (!btn) return false;"
                    "  btn.click();"
                    "  return true;"
                    "}",
                    [identity_label],
                )
                if not switched:
                    _log.warning("Identity switcher not found - comment will post as personal.")
                else:
                    await page.wait_for_timeout(400)
                    picked = await js_click_by_text(
                        page, '[role="listbox"], .artdeco-dropdown__content-inner', "page"
                    )
                    if not picked:
                        _log.warning("Could not select Company Page from identity dropdown.")

            await quill_insert_text(page, comment_editor, comment_text)
            await page.click(
                'button[aria-label*="Comment"][type="submit"], button[aria-label*="Post comment"]'
            )
            await page.wait_for_timeout(1500)
            return {
                "ok": True,
                "detail": "Comment submitted.",
                "extra": {
                    "as_company": comment_as_company,
                    "source_urn": activity,
                },
            }
        except Exception as e:
            raise_tool_error(e, "personal_comment_as_admin")

    @mcp.tool(
        title="Read company mentions in personal timeline",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"personal", "read", "bridge"},
    )
    async def personal_read_company_mentions(
        company_name: str,
        ctx: Context,
        max_results: int = 20,
    ) -> dict[str, object]:
        """List personal posts that tag the given company page.

        Scans your recent activity page for posts whose body contains the
        company name as a mention link. Useful to locate employee-advocacy
        posts for response/engagement.

        Args:
            company_name: Company display name (matched case-insensitively
                inside your post bodies).
            max_results: Cap on returned posts.
        """
        try:
            browser = get_browser()
            await browser.start()
            page = await browser.get_page()
            await page.goto("https://www.linkedin.com/in/me/recent-activity/all/")
            await remove_blocking_modal_outlet(page)
            await page.wait_for_timeout(1500)

            for _ in range(3):
                await page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)

            posts: list[dict[str, object]] = await page.evaluate(
                "([needle, cap]) => {"
                "  const n = needle.toLowerCase();"
                "  const nodes = Array.from("
                "    document.querySelectorAll('[data-urn^=\"urn:li:activity\"]')"
                "  );"
                "  const out = [];"
                "  for (const node of nodes) {"
                "    if (out.length >= cap) break;"
                "    const body = (node.innerText || '').toLowerCase();"
                "    if (!body.includes(n)) continue;"
                "    const text = (node.querySelector('div[dir=\"ltr\"]') || {}).innerText || '';"
                "    out.push({"
                "      urn: node.getAttribute('data-urn'),"
                "      text: text.slice(0, 500),"
                "      time: (node.querySelector('time') || {}).getAttribute?.('datetime') || null,"
                "    });"
                "  }"
                "  return out;"
                "}",
                [company_name, max_results],
            )
            return {
                "company_name": company_name,
                "count": len(posts),
                "posts": posts,
            }
        except Exception as e:
            raise_tool_error(e, "personal_read_company_mentions")


__all__ = ["register_bridge_personal_tools"]
