"""Patchright-backed provider implementations.

This is the only place that knows about LinkedIn's admin DOM. If a page
changes, this file + ``selectors/__init__.py`` are where the fix lives.

Conventions:
    * URL-direct navigation over button-clicking (URLs are more stable).
    * ``dirty_state_trigger(page)`` after any programmatic text fill -
      LinkedIn's Quill editor won't enable the Save button until a real
      input event fires.
    * Never swallow selector misses - raise ``SelectorError`` so the tool
      wrapper produces a diagnostic.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.core.exceptions import SelectorError
from linkedin_company_admin_mcp.core.utils import normalise_company_id
from linkedin_company_admin_mcp.providers.base import (
    AdminProvider,
    CreatePostRequest,
    DeletePostRequest,
    EditAboutRequest,
    EditLogoRequest,
    EditPostRequest,
    PostsProvider,
    ProviderResult,
    ReplyCommentRequest,
    ResharePostRequest,
    SchedulePostRequest,
    UpdateDetailsRequest,
)
from linkedin_company_admin_mcp.selectors import COMPANY_ADMIN_DASHBOARD

if TYPE_CHECKING:
    from patchright.async_api import Page

_log = logging.getLogger(__name__)


# --- Shared helpers -------------------------------------------------------


async def dirty_state_trigger(page: Page, locator_selector: str) -> None:
    """Fire an ``input`` event on a rich-text editor.

    Quill (LinkedIn's editor) doesn't enable the Save button until a real
    user-like input event occurs. Calling ``page.fill`` is not enough:
    we also tap space + backspace so the editor's change listener fires.
    """
    await page.press(locator_selector, "End")
    await page.press(locator_selector, "Space")
    await page.press(locator_selector, "Backspace")


async def quill_insert_text(page: Page, editor_selector: str, text: str) -> None:
    """Insert ``text`` into a Quill-based editor reliably."""
    await page.focus(editor_selector)
    # ``document.execCommand`` dispatches the Delta events Quill listens for.
    await page.evaluate(
        "([sel, t]) => {"
        "  const el = document.querySelector(sel);"
        "  if (!el) throw new Error('editor not found');"
        "  el.focus();"
        "  document.execCommand('insertText', false, t);"
        "}",
        [editor_selector, text],
    )
    await dirty_state_trigger(page, editor_selector)


# --- Admin provider -------------------------------------------------------


class BrowserAdminProvider(AdminProvider):
    """Edit page details (about, logo, website/industry/size) via the UI."""

    def __init__(self, browser: BrowserManager) -> None:
        self._browser = browser

    async def edit_about(self, request: EditAboutRequest) -> ProviderResult:
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        url = f"{COMPANY_ADMIN_DASHBOARD.format(company_id=cid)}?editPage=true&editPageActiveTab=details"
        await page.goto(url)
        textarea_sel = (
            'textarea[name="organizationDescriptionField"], textarea[aria-label*="About" i]'
        )
        try:
            await page.wait_for_selector(textarea_sel, timeout=10_000)
        except Exception as e:
            raise SelectorError(f"About textarea not found at {url}; selector drift likely.") from e
        await page.fill(textarea_sel, request.about_text)
        await dirty_state_trigger(page, textarea_sel)
        save_btn = 'button[data-test-id="org-page-edit-save"], button[aria-label="Save"]'
        try:
            await page.click(save_btn, timeout=5_000)
        except Exception as e:
            raise SelectorError("Save button not clickable on About editor.") from e
        await page.wait_for_timeout(1500)
        return ProviderResult(ok=True, detail="About section updated.")

    async def edit_logo(self, request: EditLogoRequest) -> ProviderResult:
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await page.goto(f"{COMPANY_ADMIN_DASHBOARD.format(company_id=cid)}?editPage=true")

        if request.logo_path:
            await self._upload(page, request.logo_path, aria="Logo")
        if request.banner_path:
            await self._upload(page, request.banner_path, aria="Banner")
        save_btn = 'button[aria-label="Save"]'
        await page.click(save_btn)
        await page.wait_for_timeout(2000)
        return ProviderResult(
            ok=True,
            detail="Logo/banner uploaded.",
            extra={
                "logo_path": request.logo_path,
                "banner_path": request.banner_path,
            },
        )

    async def _upload(self, page: Page, local_path: str, *, aria: str) -> None:
        import asyncio

        def _resolve_and_check(p: str) -> Path:
            resolved = Path(p).expanduser().resolve()
            if not resolved.is_file():
                raise FileNotFoundError(f"image file not found: {resolved}")
            return resolved

        path = await asyncio.to_thread(_resolve_and_check, local_path)
        input_sel = f'input[type="file"][aria-label*="{aria}" i]'
        try:
            await page.set_input_files(input_sel, str(path))
        except Exception as e:
            raise SelectorError(f"{aria} upload input not found (selector {input_sel!r}).") from e
        await page.wait_for_timeout(1500)

    async def update_details(self, request: UpdateDetailsRequest) -> ProviderResult:
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await page.goto(
            f"{COMPANY_ADMIN_DASHBOARD.format(company_id=cid)}?editPage=true&editPageActiveTab=details"
        )
        changes: dict[str, object] = {}

        if request.website:
            sel = 'input[name="websiteUrl"], input[aria-label*="Website" i]'
            await page.fill(sel, request.website)
            changes["website"] = request.website
        if request.industry:
            sel = 'input[aria-label*="Industry" i], input[name="industryV2"]'
            await page.fill(sel, request.industry)
            changes["industry"] = request.industry
        if request.size_range:
            sel = 'select[aria-label*="size" i], select[name="staffCountRange"]'
            await page.select_option(sel, label=request.size_range)
            changes["size_range"] = request.size_range
        if request.specialties:
            sel = 'input[aria-label*="specialt" i]'
            await page.fill(sel, ", ".join(request.specialties))
            changes["specialties"] = request.specialties

        if not changes:
            return ProviderResult(ok=False, detail="No fields requested for update.")
        save_btn = 'button[data-test-id="org-page-edit-save"], button[aria-label="Save"]'
        await page.click(save_btn)
        await page.wait_for_timeout(1500)
        return ProviderResult(ok=True, detail="Page details updated.", extra=changes)


# --- Posts provider (stubbed for Faza 3; real implementation lands Faza 4) --


class BrowserPostsProvider(PostsProvider):
    """Stub implementation so tools/company_content.py can register.

    Each method raises ``NotImplementedError``; Faza 4 fills them in with
    Quill workarounds + artdeco-modal-outlet handling (RCA documented).
    """

    def __init__(self, browser: BrowserManager) -> None:
        self._browser = browser

    async def create_post(self, request: CreatePostRequest) -> ProviderResult:
        raise NotImplementedError("BrowserPostsProvider.create_post - Faza 4")

    async def edit_post(self, request: EditPostRequest) -> ProviderResult:
        raise NotImplementedError("BrowserPostsProvider.edit_post - Faza 4")

    async def delete_post(self, request: DeletePostRequest) -> ProviderResult:
        raise NotImplementedError("BrowserPostsProvider.delete_post - Faza 4")

    async def schedule_post(self, request: SchedulePostRequest) -> ProviderResult:
        raise NotImplementedError("BrowserPostsProvider.schedule_post - Faza 4")

    async def reply_to_comment(self, request: ReplyCommentRequest) -> ProviderResult:
        raise NotImplementedError("BrowserPostsProvider.reply_to_comment - Faza 4")

    async def reshare_post(self, request: ResharePostRequest) -> ProviderResult:
        raise NotImplementedError("BrowserPostsProvider.reshare_post - Faza 4")
