"""E2E reshare_post: find an existing post, reshare it as KETU AI, delete the reshare."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from linkedin_company_admin_mcp.config.schema import AppConfig, BrowserConfig
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.providers.base import DeletePostRequest, ResharePostRequest
from linkedin_company_admin_mcp.providers.posts import BrowserPostsProvider
from linkedin_company_admin_mcp.selectors import COMPANY_ADMIN_PAGE_POSTS

KETU = "106949933"


async def main() -> None:
    cfg = AppConfig(browser=BrowserConfig(headless=True))
    stamp = datetime.now(UTC).strftime("%H%M%S")
    thoughts = f"[reshare-e2e-{stamp}] reshared by automation, cleanup pending"

    async with BrowserManager(cfg.browser) as browser:
        posts = BrowserPostsProvider(browser)
        page = await browser.get_page()
        await page.goto(COMPANY_ADMIN_PAGE_POSTS.format(company_id=KETU))
        await page.wait_for_timeout(3500)
        urn = await page.evaluate(
            r"""() => { const c = document.querySelector('[data-urn^=\"urn:li:activity\"]'); return c ? c.getAttribute('data-urn') : null; }"""
        )
        if not urn:
            raise SystemExit("no post to reshare")
        print(f"[1/3] reshare source={urn}")
        try:
            r = await posts.reshare_post(
                ResharePostRequest(company_id=KETU, source_post_urn=urn, thoughts_text=thoughts)
            )
            print(f"      -> {r.ok} {r.detail}")
        except Exception as e:
            print(f"      FAIL: {type(e).__name__}: {e}")
            return

        print("[2/3] locate reshare on feed")
        await page.wait_for_timeout(5000)
        await page.goto(COMPANY_ADMIN_PAGE_POSTS.format(company_id=KETU))
        await page.wait_for_timeout(5000)
        reshare_urn = await page.evaluate(
            r"""(needle) => {
              for (const c of document.querySelectorAll('[data-urn^=\"urn:li:activity\"]')) {
                if ((c.innerText || '').toLowerCase().includes(needle.toLowerCase())) {
                  return c.getAttribute('data-urn');
                }
              }
              return null;
            }""",
            f"reshare-e2e-{stamp}",
        )
        print(f"      reshare_urn={reshare_urn}")

        if reshare_urn:
            print("[3/3] delete reshare")
            d = await posts.delete_post(DeletePostRequest(company_id=KETU, post_urn=reshare_urn))
            print(f"      -> {d.detail}")


if __name__ == "__main__":
    asyncio.run(main())
