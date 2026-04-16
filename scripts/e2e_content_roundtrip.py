"""E2E round-trip: create_post -> list to find URN -> edit_post -> delete_post.

Runs against KETU AI (company id 106949933) using the persistent profile.
Headless by default. Invoke with ``uv run python -m scripts.e2e_content_roundtrip``.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime

from linkedin_company_admin_mcp.config.schema import AppConfig, BrowserConfig
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.providers.base import (
    CreatePostRequest,
    DeletePostRequest,
    EditPostRequest,
)
from linkedin_company_admin_mcp.providers.posts import BrowserPostsProvider
from linkedin_company_admin_mcp.selectors import COMPANY_ADMIN_PAGE_POSTS

KETU = "106949933"


async def _latest_post_urn(page, expected_fragment: str) -> str | None:
    """Return the newest admin post URN whose text contains the fragment."""

    await page.goto(COMPANY_ADMIN_PAGE_POSTS.format(company_id=KETU))
    await page.wait_for_timeout(3500)
    data = await page.evaluate(
        r"""(needle) => {
          const containers = document.querySelectorAll('[data-urn^="urn:li:activity"]');
          for (const c of containers) {
            const txt = (c.innerText || '').toLowerCase();
            if (txt.includes(needle.toLowerCase())) {
              return { urn: c.getAttribute('data-urn'), sample: txt.slice(0, 120) };
            }
          }
          return null;
        }""",
        expected_fragment,
    )
    if not data:
        return None
    return data["urn"]


async def main() -> None:
    cfg = AppConfig(browser=BrowserConfig(headless=True))
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    tag = f"ketu-e2e-{stamp}"
    initial = f"[{tag}] automated round-trip test - will be edited then deleted"
    edited = f"[{tag}] EDITED via edit_post, about to be deleted"

    async with BrowserManager(cfg.browser) as browser:
        posts = BrowserPostsProvider(browser)

        print(f"[1/4] create_post tag={tag}")
        t0 = time.monotonic()
        r1 = await posts.create_post(CreatePostRequest(company_id=KETU, text=initial))
        print(f"      -> {r1.detail} ({time.monotonic() - t0:.1f}s)")

        page = await browser.get_page()
        print("[2/4] locate URN of freshly created post")
        urn = None
        for attempt in range(4):
            await page.wait_for_timeout(2000 if attempt else 2500)
            urn = await _latest_post_urn(page, tag)
            if urn:
                break
            print(f"      attempt {attempt + 1}: not indexed yet")
        if not urn:
            raise SystemExit("FAIL: freshly created post not visible on admin page.")
        print(f"      -> urn={urn}")

        print("[3/4] edit_post")
        t0 = time.monotonic()
        r2 = await posts.edit_post(EditPostRequest(company_id=KETU, post_urn=urn, new_text=edited))
        print(f"      -> {r2.detail} ({time.monotonic() - t0:.1f}s)")

        print("[4/4] delete_post")
        t0 = time.monotonic()
        r3 = await posts.delete_post(DeletePostRequest(company_id=KETU, post_urn=urn))
        print(f"      -> {r3.detail} ({time.monotonic() - t0:.1f}s)")

        # Sanity check: URN should no longer appear on admin page.
        still = await _latest_post_urn(page, tag)
        print(
            json.dumps(
                {
                    "create_ok": r1.ok,
                    "edit_ok": r2.ok,
                    "delete_ok": r3.ok,
                    "urn": urn,
                    "still_present": bool(still),
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
