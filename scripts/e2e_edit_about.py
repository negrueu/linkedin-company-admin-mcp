"""E2E edit_about: read current -> set new -> verify -> restore."""

from __future__ import annotations

import asyncio

from linkedin_company_admin_mcp.config.schema import AppConfig, BrowserConfig
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.providers.admin import BrowserAdminProvider
from linkedin_company_admin_mcp.providers.base import EditAboutRequest
from linkedin_company_admin_mcp.selectors import COMPANY_ADMIN_EDIT_MODAL

KETU = "106949933"


async def main() -> None:
    cfg = AppConfig(browser=BrowserConfig(headless=True))
    async with BrowserManager(cfg.browser) as browser:
        admin = BrowserAdminProvider(browser)
        page = await browser.get_page()

        # Read original
        await page.goto(
            COMPANY_ADMIN_EDIT_MODAL.format(company_id=KETU), wait_until="domcontentloaded"
        )
        await page.wait_for_selector('[role="dialog"]', timeout=15_000)
        await page.wait_for_timeout(2500)
        # Activate Details tab before reading the description.
        await page.evaluate(
            r"""() => {
              const tab = Array.from(document.querySelectorAll('[role="dialog"] [role="tab"]')).find(t => (t.textContent || '').trim() === 'Details');
              if (tab) tab.click();
            }"""
        )
        await page.wait_for_timeout(1000)
        original = await page.evaluate(
            r"""() => {
              const t = document.querySelector('#organization-description-field');
              return t ? t.value : null;
            }"""
        )
        print(f"original about: len={len(original) if original else 0}")

        # LinkedIn enforces a minimum length of ~200 chars for company
        # descriptions. Anything shorter is silently rejected (Save
        # appears to succeed but the value is discarded server-side).
        probe = (
            "KETU AI SRL ofera servicii de automatizare a proceselor de business "
            "prin solutii bazate pe inteligenta artificiala. Construim agenti, "
            "integrari API si interfete conversationale pentru PME-urile care "
            "doresc o productivitate inalta. [e2e-touch]"
        )
        print(f"[1/3] set probe (len={len(probe)})")
        r = await admin.edit_about(EditAboutRequest(company_id=KETU, about_text=probe))
        print(f"      -> {r.ok} {r.detail}")

        # Re-read and verify
        await page.goto(
            COMPANY_ADMIN_EDIT_MODAL.format(company_id=KETU), wait_until="domcontentloaded"
        )
        await page.wait_for_selector('[role="dialog"]', timeout=15_000)
        await page.wait_for_timeout(2500)
        after = await page.evaluate(
            r"""() => {
              const t = document.querySelector('#organization-description-field');
              return t ? t.value : null;
            }"""
        )
        print(f"      after: len={len(after) if after else 0} match={after == probe}")

        # Restore
        print("[2/3] restore original")
        restore_text = original or ""
        r2 = await admin.edit_about(EditAboutRequest(company_id=KETU, about_text=restore_text))
        print(f"      -> {r2.ok} {r2.detail}")

        # Verify restore
        await page.goto(
            COMPANY_ADMIN_EDIT_MODAL.format(company_id=KETU), wait_until="domcontentloaded"
        )
        await page.wait_for_selector('[role="dialog"]', timeout=15_000)
        await page.wait_for_timeout(2500)
        final = await page.evaluate(
            r"""() => {
              const t = document.querySelector('#organization-description-field');
              return t ? t.value : null;
            }"""
        )
        print(f"[3/3] final: match_original={final == original}")


if __name__ == "__main__":
    asyncio.run(main())
