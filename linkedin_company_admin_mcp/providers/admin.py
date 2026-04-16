"""Patchright implementation of ``AdminProvider``.

All three admin write tools (About, logo/banner, details) operate through
the single ``?editPage=true`` Edit Page modal. Root-cause notes for why
each selector looks the way it does live next to the selector constants.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.core.exceptions import SelectorError
from linkedin_company_admin_mcp.core.utils import normalise_company_id
from linkedin_company_admin_mcp.providers.base import (
    AdminProvider,
    EditAboutRequest,
    EditLogoRequest,
    ProviderResult,
    UpdateDetailsRequest,
)
from linkedin_company_admin_mcp.selectors import (
    COMPANY_ADMIN_EDIT_MODAL,
    EDIT_FIELD_DESCRIPTION,
    EDIT_FIELD_INDUSTRY,
    EDIT_FIELD_PHONE,
    EDIT_FIELD_SIZE,
    EDIT_FIELD_TAGLINE,
    EDIT_FIELD_WEBSITE,
    EDIT_MODAL_DIALOG,
)

if TYPE_CHECKING:
    from patchright.async_api import Page

_log = logging.getLogger(__name__)


async def _open_edit_modal(page: Page, company_id: str) -> None:
    """Land on the admin dashboard and wait for the Edit Page modal."""

    await page.goto(
        COMPANY_ADMIN_EDIT_MODAL.format(company_id=company_id),
        wait_until="domcontentloaded",
        timeout=30_000,
    )
    await page.wait_for_selector(EDIT_MODAL_DIALOG, timeout=15_000)
    await page.wait_for_timeout(2500)


async def _activate_tab(page: Page, tab_name: str) -> None:
    """Click the named vertical tab inside the Edit Page modal.

    Tabs are ``role="tab"`` buttons with visible text ("Page info",
    "Details", "Workplace", ...). Once active, their sibling tabpanel's
    form controls become visible and focusable.
    """

    clicked = await page.evaluate(
        r"""(name) => {
          const dlg = document.querySelector('[role="dialog"]');
          if (!dlg) return false;
          const tab = Array.from(dlg.querySelectorAll('[role="tab"]'))
            .find(t => (t.textContent || '').trim().toLowerCase() === name.toLowerCase());
          if (!tab) return false;
          tab.click();
          return true;
        }""",
        tab_name,
    )
    if not clicked:
        raise SelectorError(f"Edit Page tab {tab_name!r} not found.")
    await page.wait_for_timeout(800)


async def _keyboard_replace(page: Page, selector: str, value: str) -> None:
    """Focus a field, clear it, type the new value.

    We route everything through the keyboard (rather than ``page.fill``)
    because Ember binds on ``input`` + ``keydown`` and a programmatic
    ``value = ...`` set via the DOM does not flip the dirty-state flag
    that enables the Save button.
    """

    await page.focus(selector)
    await page.keyboard.press("Control+A")
    await page.keyboard.press("Delete")
    if value:
        await page.keyboard.type(value, delay=15)


async def _click_save(page: Page) -> None:
    """Find the primary Save button anywhere on the page and click it.

    LinkedIn renders the Save inside the modal's footer but without
    ``role="button"``, ``data-test-id`` or an aria-label, so we locate it
    by the (artdeco-button--primary class + text = "Save") combo.

    Server-side validation errors (e.g. "Website URL is required.") are
    surfaced via toast + inline feedback. After clicking we wait briefly
    and check; if an error appears we re-raise as ``SelectorError`` so
    the tool reports the real reason rather than silently succeeding.
    """

    clicked = await page.evaluate(
        r"""() => {
          const btn = Array.from(document.querySelectorAll('button.artdeco-button--primary'))
            .find(b => /^save$/i.test((b.textContent || '').trim()) && !b.disabled);
          if (!btn) return false;
          btn.click();
          return true;
        }"""
    )
    if not clicked:
        raise SelectorError(
            "Save button on Edit Page modal not clickable - "
            "either the field did not dirty properly or LinkedIn disabled Save."
        )
    await page.wait_for_timeout(1500)
    errors: list[str] = await page.evaluate(
        r"""() => {
          const all = new Set();
          for (const t of document.querySelectorAll('.artdeco-toast-item, [role="alert"], .artdeco-inline-feedback--error')) {
            const s = (t.innerText || '').trim();
            if (s) all.add(s);
          }
          return Array.from(all);
        }"""
    )
    failure = next(
        (
            e
            for e in errors
            if any(w in e.lower() for w in ("required", "invalid", "error", "must ", "cannot"))
        ),
        None,
    )
    if failure:
        raise SelectorError(f"LinkedIn rejected Save: {failure}")


class BrowserAdminProvider(AdminProvider):
    """Edit page details via the ``?editPage=true`` modal."""

    def __init__(self, browser: BrowserManager) -> None:
        self._browser = browser

    async def edit_about(self, request: EditAboutRequest) -> ProviderResult:
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await _open_edit_modal(page, cid)
        # The description textarea lives on the "Details" tab, not the
        # default "Page info" tab. Tagline is on Page info (separate field).
        await _activate_tab(page, "Details")
        try:
            await page.wait_for_selector(EDIT_FIELD_DESCRIPTION, timeout=8_000)
        except Exception as e:
            raise SelectorError(f"Description field {EDIT_FIELD_DESCRIPTION!r} not found.") from e
        await _keyboard_replace(page, EDIT_FIELD_DESCRIPTION, request.about_text)
        await page.wait_for_timeout(600)
        await _click_save(page)
        await page.wait_for_timeout(2500)
        return ProviderResult(ok=True, detail="About section updated.")

    async def edit_logo(self, request: EditLogoRequest) -> ProviderResult:
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await _open_edit_modal(page, cid)

        if request.logo_path:
            await self._upload(page, request.logo_path, aria="Logo")
        if request.banner_path:
            await self._upload(page, request.banner_path, aria="Banner")
        await _click_save(page)
        await page.wait_for_timeout(2500)
        return ProviderResult(
            ok=True,
            detail="Logo/banner uploaded.",
            extra={
                "logo_path": request.logo_path,
                "banner_path": request.banner_path,
            },
        )

    async def _upload(self, page: Page, local_path: str, *, aria: str) -> None:
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
            raise SelectorError(f"{aria} upload input not found ({input_sel!r}).") from e
        await page.wait_for_timeout(1500)

    async def update_details(self, request: UpdateDetailsRequest) -> ProviderResult:
        cid = normalise_company_id(request.company_id)
        page = await self._browser.get_page()
        await _open_edit_modal(page, cid)
        # All fields below live on the Details tab.
        await _activate_tab(page, "Details")
        changes: dict[str, object] = {}

        if request.website:
            await _keyboard_replace(page, EDIT_FIELD_WEBSITE, request.website)
            changes["website"] = request.website
        if request.industry:
            # Industry is a typeahead - type then press Enter to accept
            # the first suggestion.
            await _keyboard_replace(page, EDIT_FIELD_INDUSTRY, request.industry)
            await page.wait_for_timeout(800)
            await page.keyboard.press("ArrowDown")
            await page.keyboard.press("Enter")
            changes["industry"] = request.industry
        if request.size_range:
            await page.select_option(EDIT_FIELD_SIZE, label=request.size_range)
            changes["size_range"] = request.size_range
        if request.specialties:
            # Specialties input lives in a separate tab/section; when it's
            # the only one supplied, LinkedIn also exposes it under the
            # phone field on the Details tab. Try the plain tagline as a
            # fallback target to keep the tool tolerant.
            specialties_sel = 'input[aria-label*="Specialt" i], input[placeholder*="Specialt" i]'
            try:
                await _keyboard_replace(page, specialties_sel, ", ".join(request.specialties))
                changes["specialties"] = request.specialties
            except Exception:
                _log.warning("specialties field not found; skipping")

        # Phone included as optional for symmetry with EDIT_FIELD_PHONE.
        phone = getattr(request, "phone", None)
        if phone:
            await _keyboard_replace(page, EDIT_FIELD_PHONE, phone)
            changes["phone"] = phone
        # Tagline is often one of the things callers want to update but
        # the current dataclass doesn't carry it; only wire it in if the
        # request object grows the attribute later.
        tagline = getattr(request, "tagline", None)
        if tagline is not None:
            await _keyboard_replace(page, EDIT_FIELD_TAGLINE, tagline)
            changes["tagline"] = tagline

        if not changes:
            return ProviderResult(ok=False, detail="No fields requested for update.")
        await page.wait_for_timeout(600)
        await _click_save(page)
        await page.wait_for_timeout(2000)
        return ProviderResult(ok=True, detail="Page details updated.", extra=changes)
