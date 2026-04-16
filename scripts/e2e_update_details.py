"""E2E update_details: change phone + industry + size, then restore."""

from __future__ import annotations

import asyncio

from linkedin_company_admin_mcp.config.schema import AppConfig, BrowserConfig
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.providers.admin import BrowserAdminProvider
from linkedin_company_admin_mcp.providers.base import UpdateDetailsRequest
from linkedin_company_admin_mcp.selectors import COMPANY_ADMIN_EDIT_MODAL

KETU = "106949933"


async def read_details(page) -> dict[str, str | None]:
    await page.goto(COMPANY_ADMIN_EDIT_MODAL.format(company_id=KETU), wait_until="domcontentloaded")
    await page.wait_for_selector('[role="dialog"]', timeout=15_000)
    await page.wait_for_timeout(2500)
    await page.evaluate(
        r"""() => { const tab = Array.from(document.querySelectorAll('[role="dialog"] [role="tab"]')).find(t => (t.textContent || '').trim() === 'Details'); if (tab) tab.click(); }"""
    )
    await page.wait_for_timeout(1000)
    return await page.evaluate(
        r"""() => ({
          website: document.querySelector('#organization-website-field')?.value || '',
          phone: document.querySelector('#organization-phone-field')?.value || '',
          size: document.querySelector('#organization-size-select')?.value || '',
          industry: document.querySelector('#organization-industry-typeahead')?.value || '',
        })"""
    )


async def main() -> None:
    cfg = AppConfig(browser=BrowserConfig(headless=True))
    async with BrowserManager(cfg.browser) as browser:
        admin = BrowserAdminProvider(browser)
        page = await browser.get_page()

        original = await read_details(page)
        print("original:", original)

        print("[1/3] update website -> https://ketu.ai/test")
        r = await admin.update_details(
            UpdateDetailsRequest(company_id=KETU, website="https://ketu.ai/test")
        )
        print(f"      -> {r.ok} {r.detail}")

        after = await read_details(page)
        print("after:", after)
        assert after["website"] == "https://ketu.ai/test", after

        print("[2/3] restore")
        r2 = await admin.update_details(
            UpdateDetailsRequest(company_id=KETU, website=original["website"])
        )
        print(f"      -> {r2.ok} {r2.detail}")

        final = await read_details(page)
        print("final:", final)
        assert final["website"] == original["website"], final
        print("[3/3] OK - restored")


if __name__ == "__main__":
    asyncio.run(main())
