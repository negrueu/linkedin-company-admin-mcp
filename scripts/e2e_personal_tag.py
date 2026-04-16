"""E2E personal_tag_company: post a personal update tagging KETU, then delete it."""

from __future__ import annotations

import asyncio
import urllib.parse
from datetime import UTC, datetime

from linkedin_company_admin_mcp.config.schema import AppConfig, BrowserConfig
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.providers.shared import dirty_state_trigger, quill_insert_text
from linkedin_company_admin_mcp.tools.bridge_personal import (
    _insert_company_mention,
    _open_personal_composer,
)


async def main() -> None:
    cfg = AppConfig(browser=BrowserConfig(headless=True))
    stamp = datetime.now(UTC).strftime("%H%M%S")
    lead = f"[tag-e2e-{stamp}] testing automated tag-company flow, will be deleted."

    async with BrowserManager(cfg.browser) as browser:
        page = await browser.get_page()
        print("[1/3] open composer + compose")
        await _open_personal_composer(page)
        editor = 'div.artdeco-modal .ql-editor[role="textbox"], div.artdeco-modal div.ql-editor'
        await quill_insert_text(page, editor, lead + " ")
        await _insert_company_mention(page, "KETU AI SRL")
        await quill_insert_text(page, editor, " is our company page.")
        await dirty_state_trigger(page, editor)
        await page.wait_for_timeout(600)

        clicked = await page.evaluate(
            r"""() => {
              const btn = document.querySelector('div.artdeco-modal button.share-actions__primary-action, div.artdeco-modal button.artdeco-button--primary');
              if (!btn || btn.disabled) return false;
              btn.click();
              return true;
            }"""
        )
        print(f"[2/3] post click: {clicked}")
        await page.wait_for_timeout(4000)

        # Now locate the post on personal profile /in/me/recent-activity/all/
        await page.goto(
            "https://www.linkedin.com/in/me/recent-activity/all/",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await page.wait_for_timeout(4000)
        urn = await page.evaluate(
            r"""(needle) => {
              for (const c of document.querySelectorAll('[data-urn^=\"urn:li:activity\"]')) {
                if ((c.innerText || '').toLowerCase().includes(needle.toLowerCase())) {
                  return c.getAttribute('data-urn');
                }
              }
              return null;
            }""",
            f"tag-e2e-{stamp}",
        )
        print(f"      personal URN: {urn}")
        if urn:
            print("[3/3] delete via personal update URL")
            encoded = urllib.parse.quote(
                urn.replace("urn:li:activity:", "urn:li:activity:"), safe=""
            )
            await page.goto(
                f"https://www.linkedin.com/feed/update/{encoded}/",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            await page.wait_for_timeout(4000)
            res = await page.evaluate(
                r"""async () => {
                  const menu = document.querySelector('button[aria-label^="Open control menu"]');
                  if (!menu) return { phase: 'menu' };
                  menu.click();
                  await new Promise(r => setTimeout(r, 1500));
                  const li = document.querySelector('li.option-delete');
                  if (!li) return { phase: 'deleteItem' };
                  const btn = li.querySelector('[role="button"]') || li;
                  btn.click();
                  await new Promise(r => setTimeout(r, 3000));
                  const confirm = Array.from(document.querySelectorAll('[role="alertdialog"] button, [role="dialog"] button'))
                    .find(b => /^delete$/i.test((b.textContent || '').trim()) && !b.disabled);
                  if (!confirm) return { phase: 'confirm' };
                  confirm.click();
                  await new Promise(r => setTimeout(r, 2000));
                  return { ok: true };
                }"""
            )
            print(f"      cleanup: {res}")


if __name__ == "__main__":
    asyncio.run(main())
