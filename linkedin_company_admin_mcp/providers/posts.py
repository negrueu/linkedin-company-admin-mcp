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
        """Schedule a company post for a future date/time.

        Flow (validated 2026-04-17 against KETU AI):
            1. Open composer, write body, trigger dirty state.
            2. Click ``button.share-actions__scheduled-post-btn``
               (aria-label "Schedule post") to open the schedule dialog.
            3. Fill ``input#share-post__scheduled-date`` (mm/dd/yyyy,
               US format - must be converted from the caller's ISO date)
               and ``input#share-post__scheduled-time`` (e.g. "10:30 AM").
            4. Click "Next" to advance to the review step.
            5. Click "Schedule" on the review step to commit.
        """
        if "T" not in request.scheduled_at_iso:
            raise ValueError("scheduled_at_iso must be ISO 8601 with date and time.")
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await _open_company_composer(page, cid)
        await quill_insert_text(page, _COMPOSER_EDITOR, request.text)
        await dirty_state_trigger(page, _COMPOSER_EDITOR)
        await page.wait_for_timeout(400)

        opened = await page.evaluate(
            r"""() => {
              const btn = document.querySelector(
                '[role="dialog"] button.share-actions__scheduled-post-btn,'
                + ' [role="dialog"] button[aria-label="Schedule post"]'
              );
              if (!btn) return false;
              btn.click();
              return true;
            }"""
        )
        if not opened:
            raise SelectorError("'Schedule post' button not found on composer.")
        await page.wait_for_selector("#share-post__scheduled-date", timeout=10_000)

        date_iso, time_iso = request.scheduled_at_iso.split("T", 1)
        year, month, day = date_iso.split("-")
        us_date = f"{int(month):02d}/{int(day):02d}/{year}"
        hh, mm = time_iso[:5].split(":")
        hour_24 = int(hh)
        ampm = "AM" if hour_24 < 12 else "PM"
        hour_12 = hour_24 % 12 or 12
        us_time = f"{hour_12}:{mm} {ampm}"

        await page.fill("#share-post__scheduled-date", us_date)
        await page.keyboard.press("Tab")
        await page.fill("#share-post__scheduled-time", us_time)
        await page.keyboard.press("Tab")
        await page.wait_for_timeout(400)

        next_clicked = await page.evaluate(
            r"""() => {
              const dlgs = Array.from(document.querySelectorAll('[role="dialog"]'));
              const dlg = dlgs[dlgs.length - 1];
              if (!dlg) return false;
              const btn = Array.from(dlg.querySelectorAll('button')).find(b =>
                /^next$/i.test((b.textContent || '').trim()) && !b.disabled
              );
              if (!btn) return false;
              btn.click();
              return true;
            }"""
        )
        if not next_clicked:
            raise SelectorError("Schedule dialog 'Next' button not clickable - invalid date/time?")
        await page.wait_for_timeout(1200)

        confirmed = await page.evaluate(
            r"""() => {
              const dlgs = Array.from(document.querySelectorAll('[role="dialog"]'));
              const dlg = dlgs[dlgs.length - 1];
              if (!dlg) return false;
              const btn = Array.from(dlg.querySelectorAll('button')).find(b => {
                const t = (b.textContent || '').trim().toLowerCase();
                return t === 'schedule' && !b.disabled;
              });
              if (!btn) return false;
              btn.click();
              return true;
            }"""
        )
        if not confirmed:
            raise SelectorError("Schedule review 'Schedule' button not clickable.")
        await page.wait_for_timeout(2500)
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
        """Reshare another post on the company's feed, with optional thoughts.

        Flow (validated 2026-04-17 on KETU AI):
            1. Open ``/feed/update/<activity>/``.
            2. Click ``button.social-actions-button`` whose text is
               "Repost" (the post-detail page exposes a dropdown
               trigger, not a plain submit button).
            3. In the opened dropdown, click the item whose text matches
               "Repost with your thoughts" (inside the
               ``.artdeco-dropdown__content--is-open`` wrapper only).
            4. The composer opens with the PERSONAL actor selected by
               default. Click ``button.share-unified-settings-entry-button``
               to open Post Settings, click the
               ``share-unified-settings-menu__actor-toggle``, then the
               radio whose text matches "<Company name>", click Save,
               click Done to return to the composer.
            5. Type the thoughts into the dialog-scoped Quill editor and
               click the primary Post button.
        """
        if not is_valid_urn(request.source_post_urn):
            raise ValueError(f"Invalid source URN: {request.source_post_urn!r}")
        page = await self._browser.get_page()
        activity = extract_activity_urn(request.source_post_urn)
        if activity is None:
            raise ValueError(f"Unable to extract activity id from {request.source_post_urn!r}")
        cid = normalise_company_id(request.company_id)
        encoded = urllib.parse.quote(activity, safe="")
        await page.goto(
            f"https://www.linkedin.com/feed/update/{encoded}/",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await page.wait_for_timeout(4000)

        step = await page.evaluate(
            r"""async () => {
              const triggers = Array.from(document.querySelectorAll('button.social-actions-button'))
                .filter(b => (b.textContent || '').trim().toLowerCase() === 'repost');
              if (!triggers.length) return { phase: 'no-repost-trigger' };
              triggers[0].click();
              await new Promise(r => setTimeout(r, 1500));
              const dd = Array.from(document.querySelectorAll('.artdeco-dropdown__content--is-open'))
                .find(el => el.offsetParent !== null);
              if (!dd) return { phase: 'no-open-dropdown' };
              const item = Array.from(dd.querySelectorAll('.artdeco-dropdown__item, [role="button"]'))
                .find(el => /repost with your thoughts/i.test((el.innerText || '').trim()));
              if (!item) return { phase: 'no-thoughts-item' };
              item.click();
              return { ok: true };
            }"""
        )
        if not step.get("ok"):
            raise SelectorError(f"Reshare entry flow stopped at {step.get('phase')!r}.")

        await page.wait_for_selector(_COMPOSER_DIALOG, timeout=12_000)
        await page.wait_for_selector(_COMPOSER_EDITOR, timeout=12_000)
        await page.wait_for_timeout(800)

        # Switch actor to the company. Use cid in the radio match so the flow
        # works for any company, not just KETU.
        switched = await page.evaluate(
            r"""async (companyId) => {
              const dlg = document.querySelector('[role="dialog"]');
              const entry = dlg.querySelector('button.share-unified-settings-entry-button');
              if (!entry) return { phase: 'no-entry' };
              if (entry.textContent.includes(String(companyId))) {
                // already in company context (unlikely here, but bail gracefully)
                return { ok: true, alreadyCompany: true };
              }
              entry.click();
              await new Promise(r => setTimeout(r, 1500));
              const toggle = document.querySelector('button.share-unified-settings-menu__actor-toggle');
              if (!toggle) return { phase: 'no-actor-toggle' };
              toggle.click();
              await new Promise(r => setTimeout(r, 1800));

              // Pick the organization radio. Match either by text "KETU" or
              // by position (personal is radio[0], first company is [1]).
              const dialogs = Array.from(document.querySelectorAll('[role="dialog"]'));
              const last = dialogs[dialogs.length - 1];
              const radios = Array.from(last.querySelectorAll('button[role="radio"]'));
              const orgRadio = radios.find(r => r.getAttribute('aria-checked') === 'false' && !/^(Connections|Anyone)/i.test((r.innerText || '').trim()));
              if (!orgRadio) return { phase: 'no-org-radio', count: radios.length };
              orgRadio.click();
              await new Promise(r => setTimeout(r, 400));

              // Save (actor picker step)
              const save = Array.from(last.querySelectorAll('button')).find(b =>
                /^save$/i.test((b.textContent || '').trim()) && !b.disabled
              );
              if (!save) return { phase: 'no-save' };
              save.click();
              await new Promise(r => setTimeout(r, 1200));

              // Back on Post Settings: click Done
              const done = Array.from(document.querySelectorAll('[role="dialog"] button')).find(b =>
                /^done$/i.test((b.textContent || '').trim()) && !b.disabled && b.offsetParent !== null
              );
              if (!done) return { phase: 'no-done' };
              done.click();
              await new Promise(r => setTimeout(r, 1000));
              return { ok: true };
            }""",
            cid,
        )
        if not switched.get("ok"):
            raise SelectorError(f"Actor switch flow stopped at {switched.get('phase')!r}.")

        # Compose and post
        if request.thoughts_text:
            await quill_insert_text(page, _COMPOSER_EDITOR, request.thoughts_text)
            await dirty_state_trigger(page, _COMPOSER_EDITOR)
            await page.wait_for_timeout(400)

        clicked = await page.evaluate(
            r"""() => {
              const btn = document.querySelector(
                '[role="dialog"] button.share-actions__primary-action,'
                + ' [role="dialog"] button.artdeco-button--primary'
              );
              if (!btn || btn.disabled) return false;
              btn.click();
              return true;
            }"""
        )
        if not clicked:
            raise SelectorError("Primary Post button in reshare composer not clickable.")
        await page.wait_for_timeout(3000)
        return ProviderResult(
            ok=True, detail="Post reshared as company.", extra={"source_urn": activity}
        )
