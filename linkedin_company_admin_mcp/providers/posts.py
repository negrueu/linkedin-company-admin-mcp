"""Patchright implementation of ``PostsProvider``.

This is the piece where v1 spent dozens of failed commits on
``delete_post`` because of a phantom ``#artdeco-modal-outlet`` overlay.
Root cause + fix documented in ``providers/shared.remove_blocking_modal_outlet``.

Every tool here follows the same skeleton:
    1. Navigate to a stable URL (not click a dynamic button).
    2. Remove stray modal outlets.
    3. Interact through either the Playwright locator API or a direct
       ``page.evaluate`` click when actionability checks are intolerant.
    4. Wait for a success signal (toast, URL change, DOM update).
"""

from __future__ import annotations

import logging
import urllib.parse

from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.core.exceptions import SelectorError
from linkedin_company_admin_mcp.core.utils import (
    extract_activity_urn,
    is_valid_urn,
    normalise_company_id,
)
from linkedin_company_admin_mcp.providers.base import (
    CreatePostRequest,
    DeletePostRequest,
    EditPostRequest,
    PostsProvider,
    ProviderResult,
    ReplyCommentRequest,
    ResharePostRequest,
    SchedulePostRequest,
)
from linkedin_company_admin_mcp.providers.shared import (
    dirty_state_trigger,
    js_click_by_text,
    quill_insert_text,
    remove_blocking_modal_outlet,
)
from linkedin_company_admin_mcp.selectors import (
    COMPANY_ADMIN_PAGE_POSTS,
)

_log = logging.getLogger(__name__)

# Composer constants -------------------------------------------------------
_COMPOSER_EDITOR = 'div.ql-editor, div[role="textbox"][contenteditable="true"]'
_COMPOSER_POST_BUTTON = 'button[aria-label="Post"], button.share-actions__primary-action'
_COMPOSER_SCHEDULE_BUTTON = 'button[aria-label*="Schedule" i]'
_COMPOSER_SCHEDULE_DATE = 'input[aria-label*="date" i], input[type="date"]'
_COMPOSER_SCHEDULE_TIME = 'input[aria-label*="time" i], input[type="time"]'


class BrowserPostsProvider(PostsProvider):
    """Content tools (create / edit / delete / schedule / reply / reshare)."""

    def __init__(self, browser: BrowserManager) -> None:
        self._browser = browser

    # --- create -----------------------------------------------------------

    async def create_post(self, request: CreatePostRequest) -> ProviderResult:
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await page.goto(
            f"{COMPANY_ADMIN_PAGE_POSTS.format(company_id=cid)}?share=true"
            "&shareActorType=ORGANIZATION"
        )
        await remove_blocking_modal_outlet(page)

        await page.wait_for_selector(_COMPOSER_EDITOR, timeout=15_000)
        await quill_insert_text(page, _COMPOSER_EDITOR, request.text)

        # LinkedIn may show a "Post settings" dialog with Done button stuck
        # disabled. Escape dismisses it; the underlying composer is still valid.
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(400)

        try:
            await page.click(_COMPOSER_POST_BUTTON, timeout=8_000)
        except Exception as e:
            raise SelectorError(
                "Post button not clickable - LinkedIn composer may have drifted."
            ) from e
        await page.wait_for_timeout(2500)
        return ProviderResult(
            ok=True,
            detail="Post published.",
            extra={"has_link": bool(request.link_url), "has_image": bool(request.image_path)},
        )

    # --- edit -------------------------------------------------------------

    async def edit_post(self, request: EditPostRequest) -> ProviderResult:
        if not is_valid_urn(request.post_urn):
            raise ValueError(f"Invalid post URN: {request.post_urn!r}")
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await page.goto(COMPANY_ADMIN_PAGE_POSTS.format(company_id=cid))
        await remove_blocking_modal_outlet(page)

        post_sel = f'[data-urn="{request.post_urn}"]'
        try:
            await page.wait_for_selector(post_sel, timeout=10_000)
        except Exception as e:
            raise SelectorError(f"Post {request.post_urn!r} not found on page.") from e

        menu_clicked = await js_click_by_text(page, post_sel, "Edit post")
        if not menu_clicked:
            await page.click(f'{post_sel} button[aria-label*="control menu" i]')
            await page.wait_for_timeout(500)
            menu_clicked = await js_click_by_text(page, "body", "Edit post")
        if not menu_clicked:
            raise SelectorError("'Edit post' menu item not found.")

        await page.wait_for_selector(_COMPOSER_EDITOR, timeout=8_000)
        await page.evaluate(
            f"() => {{ const e = document.querySelector({_COMPOSER_EDITOR!r});"
            " if (e) e.innerHTML = ''; }}"
        )
        await quill_insert_text(page, _COMPOSER_EDITOR, request.new_text)
        await page.click('button[aria-label="Save"], button[aria-label="Update"]')
        await page.wait_for_timeout(2000)
        return ProviderResult(ok=True, detail="Post updated.")

    # --- delete -----------------------------------------------------------

    async def delete_post(self, request: DeletePostRequest) -> ProviderResult:
        """Delete a post using a full JS click path.

        **Why JS-only?** Playwright's actionability checks are tripped by
        the ``#artdeco-modal-outlet`` overlay. See
        ``providers/shared.remove_blocking_modal_outlet`` for the full RCA.
        We remove outlets, then open the menu and click Delete by
        invoking ``.click()`` directly via ``page.evaluate`` so no
        actionability check runs against a phantom blocker.
        """
        if not is_valid_urn(request.post_urn):
            raise ValueError(f"Invalid post URN: {request.post_urn!r}")
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await page.goto(COMPANY_ADMIN_PAGE_POSTS.format(company_id=cid))
        await remove_blocking_modal_outlet(page)

        post_sel = f'[data-urn="{request.post_urn}"]'
        try:
            await page.wait_for_selector(post_sel, timeout=10_000)
        except Exception as e:
            raise SelectorError(f"Post {request.post_urn!r} not found on page.") from e

        opened = await page.evaluate(
            "(sel) => {"
            "  const root = document.querySelector(sel);"
            "  if (!root) return false;"
            "  const btn = root.querySelector("
            '    \'button[aria-label*="control menu" i], button[aria-label*="options" i]\''
            "  );"
            "  if (!btn) return false;"
            "  btn.click();"
            "  return true;"
            "}",
            post_sel,
        )
        if not opened:
            raise SelectorError("Control-menu button not found on post.")
        await page.wait_for_timeout(700)
        await remove_blocking_modal_outlet(page)

        clicked_delete = await js_click_by_text(page, "body", "Delete")
        if not clicked_delete:
            raise SelectorError("'Delete' menu item not visible after opening menu.")
        await page.wait_for_timeout(600)

        confirmed = await js_click_by_text(page, '[role="dialog"], .artdeco-modal', "Delete")
        if not confirmed:
            # Fallback: click the primary modal action.
            confirmed = await page.evaluate(
                "() => {"
                "  const btn = document.querySelector("
                "    '[data-test-dialog-primary-btn], .artdeco-modal button.artdeco-button--primary'"
                "  );"
                "  if (btn) { btn.click(); return true; }"
                "  return false;"
                "}"
            )
        if not confirmed:
            raise SelectorError("Delete confirmation button not found in modal.")
        await page.wait_for_timeout(2500)
        return ProviderResult(ok=True, detail="Post deleted.", extra={"urn": request.post_urn})

    # --- schedule --------------------------------------------------------

    async def schedule_post(self, request: SchedulePostRequest) -> ProviderResult:
        if "T" not in request.scheduled_at_iso:
            raise ValueError("scheduled_at_iso must be ISO 8601 with date and time.")
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await page.goto(
            f"{COMPANY_ADMIN_PAGE_POSTS.format(company_id=cid)}?share=true"
            "&shareActorType=ORGANIZATION"
        )
        await remove_blocking_modal_outlet(page)
        await page.wait_for_selector(_COMPOSER_EDITOR, timeout=15_000)
        await quill_insert_text(page, _COMPOSER_EDITOR, request.text)

        clicked = await js_click_by_text(page, "body", "Schedule")
        if not clicked:
            raise SelectorError("'Schedule' option not found on composer.")
        await page.wait_for_timeout(800)

        date_part, time_part = request.scheduled_at_iso.split("T", 1)
        await page.fill(_COMPOSER_SCHEDULE_DATE, date_part)
        await page.fill(_COMPOSER_SCHEDULE_TIME, time_part[:5])
        await dirty_state_trigger(page, _COMPOSER_SCHEDULE_TIME)

        submitted = await js_click_by_text(page, '[role="dialog"]', "Schedule")
        if not submitted:
            raise SelectorError("Schedule confirm button not clickable.")
        await page.wait_for_timeout(2000)
        return ProviderResult(
            ok=True, detail="Post scheduled.", extra={"at": request.scheduled_at_iso}
        )

    # --- reply to comment ------------------------------------------------

    async def reply_to_comment(self, request: ReplyCommentRequest) -> ProviderResult:
        if not is_valid_urn(request.post_urn):
            raise ValueError(f"Invalid post URN: {request.post_urn!r}")
        page = await self._browser.get_page()
        post_urn_id = extract_activity_urn(request.post_urn)
        if post_urn_id is None:
            raise ValueError(f"Unable to extract activity id from {request.post_urn!r}")
        encoded = urllib.parse.quote(post_urn_id, safe="")
        await page.goto(f"https://www.linkedin.com/feed/update/{encoded}/")
        await remove_blocking_modal_outlet(page)
        await page.wait_for_timeout(2000)

        needle = request.comment_author_name.lower()
        reply_opened = await page.evaluate(
            "([name]) => {"
            "  const lowerName = name.toLowerCase();"
            "  const comments = document.querySelectorAll('article.comments-comment-entity, [class*=\"comments-comment\"]');"
            "  for (const c of comments) {"
            "    const author = (c.innerText || '').toLowerCase();"
            "    if (author.includes(lowerName)) {"
            "      const replyBtn = c.querySelector('button[aria-label*=\"Reply\" i]');"
            "      if (replyBtn) { replyBtn.click(); return true; }"
            "    }"
            "  }"
            "  return false;"
            "}",
            [needle],
        )
        if not reply_opened:
            raise SelectorError(
                f"Comment by author containing {request.comment_author_name!r} not found."
            )
        await page.wait_for_timeout(600)

        reply_editor = 'div[role="textbox"][aria-label*="Reply" i]'
        await page.wait_for_selector(reply_editor, timeout=8_000)
        await quill_insert_text(page, reply_editor, request.reply_text)
        await page.click('button[aria-label*="Reply"][type="submit"], button[aria-label="Post"]')
        await page.wait_for_timeout(1500)
        return ProviderResult(ok=True, detail="Reply posted as page.")

    # --- reshare ---------------------------------------------------------

    async def reshare_post(self, request: ResharePostRequest) -> ProviderResult:
        if not is_valid_urn(request.source_post_urn):
            raise ValueError(f"Invalid source URN: {request.source_post_urn!r}")
        page = await self._browser.get_page()
        activity = extract_activity_urn(request.source_post_urn)
        if activity is None:
            raise ValueError(f"Unable to extract activity id from {request.source_post_urn!r}")
        encoded = urllib.parse.quote(activity, safe="")
        await page.goto(f"https://www.linkedin.com/feed/update/{encoded}/")
        await remove_blocking_modal_outlet(page)
        await page.wait_for_timeout(1200)

        opened = await js_click_by_text(page, "body", "Repost")
        if not opened:
            opened = await js_click_by_text(page, "body", "Share")
        if not opened:
            raise SelectorError("Reshare entry point not found on post.")
        await page.wait_for_timeout(500)

        clicked = await js_click_by_text(page, "body", "Repost with your thoughts")
        if not clicked:
            clicked = await js_click_by_text(page, "body", "Reshare with thoughts")
        if not clicked:
            raise SelectorError("'Repost with your thoughts' option missing.")

        await page.wait_for_selector(_COMPOSER_EDITOR, timeout=8_000)
        if request.thoughts_text:
            await quill_insert_text(page, _COMPOSER_EDITOR, request.thoughts_text)
        await page.click(_COMPOSER_POST_BUTTON)
        await page.wait_for_timeout(2000)
        return ProviderResult(ok=True, detail="Post reshared.", extra={"source_urn": activity})
