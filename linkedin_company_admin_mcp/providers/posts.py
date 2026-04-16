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
# Scope the Quill editor to the share dialog so we never pick up a comment
# editor on one of the posts rendered behind the modal.
_COMPOSER_DIALOG = '[role="dialog"]'
_COMPOSER_EDITOR = '[role="dialog"] .ql-editor[role="textbox"], [role="dialog"] div.ql-editor'
_COMPOSER_POST_BUTTON = (
    'button.share-actions__primary-action, [role="dialog"] button.artdeco-button--primary'
)
_COMPOSER_SCHEDULE_DATE = 'input[aria-label*="date" i], input[type="date"]'
_COMPOSER_SCHEDULE_TIME = 'input[aria-label*="time" i], input[type="time"]'


async def _open_company_composer(page: object, company_id: str) -> None:
    """Land on the admin posts page and click 'Start a post'.

    LinkedIn used to accept a ``?share=true&shareActorType=ORGANIZATION``
    URL parameter; it no longer auto-opens the composer (as of 2026-04).
    """

    await page.goto(COMPANY_ADMIN_PAGE_POSTS.format(company_id=company_id))  # type: ignore[attr-defined]
    await page.wait_for_timeout(2500)  # type: ignore[attr-defined]

    # Do NOT call remove_blocking_modal_outlet here: that outlet is the
    # mount point LinkedIn's Ember code uses to render the share dialog.
    # Removing it would make the dialog never appear even though the
    # click on "Start a post" succeeded. Outlet cleanup belongs only in
    # flows that interact with already-rendered modals (delete_post's
    # 3-dot menu -> confirm).
    opened = await page.evaluate(  # type: ignore[attr-defined]
        r"""async () => {
            const btns = Array.from(document.querySelectorAll('button'));
            const start = btns.find((b) => /^\s*start a post\s*$/i.test((b.textContent || '').trim()));
            if (!start) return { found: false };
            start.click();
            await new Promise(r => setTimeout(r, 2500));
            return { found: true, dialog: !!document.querySelector('[role="dialog"]') };
        }"""
    )
    if not opened.get("found"):
        raise SelectorError("'Start a post' button not found on admin posts page.")

    await page.wait_for_selector(_COMPOSER_DIALOG, timeout=15_000)  # type: ignore[attr-defined]
    await page.wait_for_selector(_COMPOSER_EDITOR, timeout=15_000)  # type: ignore[attr-defined]
    await page.wait_for_timeout(500)  # type: ignore[attr-defined]


class BrowserPostsProvider(PostsProvider):
    """Content tools (create / edit / delete / schedule / reply / reshare)."""

    def __init__(self, browser: BrowserManager) -> None:
        self._browser = browser

    # --- create -----------------------------------------------------------

    async def create_post(self, request: CreatePostRequest) -> ProviderResult:
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await _open_company_composer(page, cid)

        await quill_insert_text(page, _COMPOSER_EDITOR, request.text)
        await dirty_state_trigger(page, _COMPOSER_EDITOR)
        await page.wait_for_timeout(600)

        # A "Post settings" sub-dialog may appear over the composer (audience
        # picker, etc.) with a disabled Done button. Only press Escape if
        # we detect two stacked dialogs - pressing Escape on the single
        # main dialog would close the composer itself.
        dialog_count: int = await page.evaluate(
            "() => document.querySelectorAll('[role=\"dialog\"]').length"
        )
        if dialog_count >= 2:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(400)

        # Click via evaluate to skip actionability checks; LinkedIn
        # occasionally layers an invisible pointer-events-auto overlay on
        # the primary button which Playwright considers as "covering".
        clicked_post = await page.evaluate(
            r"""() => {
              const btn = document.querySelector(
                '[role="dialog"] button.share-actions__primary-action, [role="dialog"] button.artdeco-button--primary'
              );
              if (!btn || btn.disabled) return false;
              btn.click();
              return true;
            }"""
        )
        if not clicked_post:
            raise SelectorError("Post button not clickable - composer may have drifted.")
        await page.wait_for_timeout(3500)
        return ProviderResult(
            ok=True,
            detail="Post published.",
            extra={"has_link": bool(request.link_url), "has_image": bool(request.image_path)},
        )

    # --- edit -------------------------------------------------------------

    async def edit_post(self, request: EditPostRequest) -> ProviderResult:
        """Edit a company post via its individual update URL.

        Flow (validated 2026-04-17 alongside delete_post):
            1. Navigate to ``/feed/update/<urn>/`` for the admin menu.
            2. Open control menu; click ``li.option-edit-share > [role="button"]``
               (note: the class is ``option-edit-share`` for reshare/text
               posts, NOT ``option-edit`` as the delete variant).
            3. Fill the composer's Quill editor (scoped to the dialog).
            4. Click the ``Save`` button (which replaces Post for edits).
        """
        if not is_valid_urn(request.post_urn):
            raise ValueError(f"Invalid post URN: {request.post_urn!r}")
        normalise_company_id(request.company_id)  # validate format
        activity = extract_activity_urn(request.post_urn)
        if activity is None:
            raise ValueError(f"Cannot extract activity id from {request.post_urn!r}")
        page = await self._browser.get_page()
        encoded = urllib.parse.quote(activity, safe="")
        await page.goto(
            f"https://www.linkedin.com/feed/update/{encoded}/",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await page.wait_for_timeout(4000)

        menu_result = await page.evaluate(
            r"""async () => {
              const menuBtn = document.querySelector('button[aria-label^="Open control menu"]');
              if (!menuBtn) return { phase: 'menuBtn' };
              menuBtn.click();
              await new Promise(r => setTimeout(r, 2000));
              const li = document.querySelector('li.option-edit-share, li.option-edit');
              if (!li) return { phase: 'editItem' };
              const btn = li.querySelector('[role="button"]') || li;
              btn.click();
              return { ok: true };
            }"""
        )
        if not menu_result.get("ok"):
            raise SelectorError(f"Edit menu flow stopped at {menu_result.get('phase')!r}.")

        # Edit uses the same share-dialog structure. Wait for the editor,
        # clear old contents, insert new text, save.
        await page.wait_for_selector(_COMPOSER_DIALOG, timeout=12_000)
        await page.wait_for_selector(_COMPOSER_EDITOR, timeout=12_000)
        await page.wait_for_timeout(600)

        # LinkedIn enforces Trusted Types CSP: innerHTML = '' is rejected.
        # Use replaceChildren() + Ctrl+A fallback instead.
        await page.evaluate(
            "() => {"
            "  const e = document.querySelector("
            '    \'[role="dialog"] .ql-editor[role="textbox"], [role="dialog"] div.ql-editor\''
            "  );"
            "  if (e) { e.replaceChildren(); e.focus(); }"
            "}"
        )
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Delete")
        await page.wait_for_timeout(200)
        await quill_insert_text(page, _COMPOSER_EDITOR, request.new_text)
        await dirty_state_trigger(page, _COMPOSER_EDITOR)
        await page.wait_for_timeout(500)

        saved = await page.evaluate(
            r"""() => {
              const dlg = document.querySelector('[role="dialog"]');
              if (!dlg) return false;
              const btns = Array.from(dlg.querySelectorAll('button'));
              const save = btns.find(b => {
                const t = (b.textContent || '').trim().toLowerCase();
                return (t === 'save' || t === 'update' || t === 'post') && !b.disabled;
              });
              if (!save) return false;
              save.click();
              return true;
            }"""
        )
        if not saved:
            raise SelectorError("Save button in edit dialog not found or still disabled.")
        await page.wait_for_timeout(2500)
        return ProviderResult(ok=True, detail="Post updated.", extra={"urn": request.post_urn})

    # --- delete -----------------------------------------------------------

    async def delete_post(self, request: DeletePostRequest) -> ProviderResult:
        """Delete a company post via its individual update URL.

        Flow (validated 2026-04-17 against KETU AI):
            1. Navigate to ``/feed/update/<urn>/`` so the page-detail view
               renders the admin 3-dot menu (it is NOT exposed on the
               ``/admin/page-posts/published/`` list view).
            2. Click ``button[aria-label^="Open control menu"]`` via
               programmatic ``.click()``.
            3. Click ``li.option-delete > [role="button"]`` - the menu
               item uses ``role="button"`` on an inner div, not
               ``role="menuitem"``.
            4. Wait for a confirmation dialog and click its primary
               ``Delete`` button.
        """
        if not is_valid_urn(request.post_urn):
            raise ValueError(f"Invalid post URN: {request.post_urn!r}")
        normalise_company_id(
            request.company_id
        )  # validate, not used after - post-detail URL needs only the activity URN
        activity = extract_activity_urn(request.post_urn)
        if activity is None:
            raise ValueError(f"Cannot extract activity id from {request.post_urn!r}")
        page = await self._browser.get_page()
        encoded = urllib.parse.quote(activity, safe="")
        await page.goto(
            f"https://www.linkedin.com/feed/update/{encoded}/",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await page.wait_for_timeout(4000)

        result = await page.evaluate(
            r"""async () => {
              const menuBtn = document.querySelector('button[aria-label^="Open control menu"]');
              if (!menuBtn) return { phase: 'menuBtn' };
              menuBtn.click();
              await new Promise(r => setTimeout(r, 2000));

              const li = document.querySelector('li.option-delete');
              if (!li) return { phase: 'deleteItem' };
              const btn = li.querySelector('[role="button"]') || li;
              btn.click();
              await new Promise(r => setTimeout(r, 3500));

              const confirm = Array.from(
                document.querySelectorAll('[role="alertdialog"] button, [role="dialog"] button')
              ).find(b => {
                const t = (b.textContent || '').trim();
                return /^delete$/i.test(t) && b.offsetParent !== null;
              });
              if (!confirm) return { phase: 'confirm' };
              confirm.click();
              await new Promise(r => setTimeout(r, 2500));
              return { ok: true };
            }"""
        )
        if not result.get("ok"):
            raise SelectorError(
                f"Delete flow stopped at phase {result.get('phase')!r}. "
                "LinkedIn UI may have changed - re-introspect /feed/update/<urn>/."
            )
        await page.wait_for_timeout(1500)
        return ProviderResult(ok=True, detail="Post deleted.", extra={"urn": request.post_urn})

    # --- schedule --------------------------------------------------------

    async def schedule_post(self, request: SchedulePostRequest) -> ProviderResult:
        if "T" not in request.scheduled_at_iso:
            raise ValueError("scheduled_at_iso must be ISO 8601 with date and time.")
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await _open_company_composer(page, cid)
        await quill_insert_text(page, _COMPOSER_EDITOR, request.text)
        await dirty_state_trigger(page, _COMPOSER_EDITOR)

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
