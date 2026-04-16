"""E2E for schedule_post: schedule ~2h ahead, verify via scheduled list, cancel it."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from linkedin_company_admin_mcp.config.schema import AppConfig, BrowserConfig
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.providers.base import SchedulePostRequest
from linkedin_company_admin_mcp.providers.posts import BrowserPostsProvider

KETU = "106949933"
SCHEDULED_URL = f"https://www.linkedin.com/company/{KETU}/admin/page-posts/scheduled/"


INTROSPECT_SCHEDULED = r"""
(needle) => {
  const rows = Array.from(document.querySelectorAll('[data-urn], article, li'));
  const out = [];
  for (const r of rows) {
    const t = (r.innerText || '');
    if (!t) continue;
    if (!t.toLowerCase().includes(needle.toLowerCase())) continue;
    const urn = r.getAttribute('data-urn');
    out.push({
      urn,
      tag: r.tagName,
      classes: Array.from(r.classList).slice(0, 5),
      text: t.slice(0, 200),
    });
    if (out.length >= 3) break;
  }
  return out;
}
"""


CANCEL_VIA_MENU = r"""
async (needle) => {
  const rows = Array.from(document.querySelectorAll('[data-urn]'));
  const row = rows.find(r => (r.innerText || '').toLowerCase().includes(needle.toLowerCase()));
  if (!row) return { phase: 'row' };
  const menuBtn = row.querySelector('button[aria-label*="control menu" i], button[aria-label*="More" i]');
  if (!menuBtn) return { phase: 'menuBtn' };
  menuBtn.click();
  await new Promise(r => setTimeout(r, 1500));
  // Find a menu item with text Delete / Cancel / Discard
  const items = Array.from(document.querySelectorAll('li, [role="menuitem"], [role="button"]'));
  const del = items.find(i => {
    const t = (i.innerText || '').trim().toLowerCase();
    return t === 'delete' || t === 'cancel' || t === 'discard scheduled post' || t === 'delete scheduled post';
  });
  if (!del) return { phase: 'delItem', items: items.slice(0, 10).map(i => (i.innerText || '').trim().slice(0, 60)) };
  del.click();
  await new Promise(r => setTimeout(r, 2000));
  const confirm = Array.from(document.querySelectorAll('[role="dialog"] button, [role="alertdialog"] button')).find(b => {
    const t = (b.textContent || '').trim().toLowerCase();
    return (t === 'delete' || t === 'cancel' || t === 'confirm') && !b.disabled;
  });
  if (confirm) { confirm.click(); await new Promise(r => setTimeout(r, 1500)); }
  return { ok: true };
}
"""


async def main() -> None:
    cfg = AppConfig(browser=BrowserConfig(headless=True))
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    tag = f"ketu-sched-{stamp}"
    body = f"[{tag}] auto-scheduled test - will be cancelled"

    # LinkedIn interprets date/time fields in the browser's local timezone.
    # Use local-naive now() and add comfortable buffer (>>10 min minimum).
    target = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=4)
    bump = (15 - target.minute % 15) % 15
    target = target + timedelta(minutes=bump or 15)
    scheduled_iso = target.strftime("%Y-%m-%dT%H:%M")

    async with BrowserManager(cfg.browser) as browser:
        posts = BrowserPostsProvider(browser)
        print(f"[1/3] schedule_post at={scheduled_iso}")
        r = await posts.schedule_post(
            SchedulePostRequest(company_id=KETU, text=body, scheduled_at_iso=scheduled_iso)
        )
        print(f"      -> {r.detail}")

        page = await browser.get_page()
        await page.goto(SCHEDULED_URL)
        await page.wait_for_timeout(3500)
        print("[2/3] verify scheduled row exists")
        found = await page.evaluate(INTROSPECT_SCHEDULED, tag)
        print(f"      rows={len(found)}")
        for f in found:
            print("      >", f.get("urn"), "|", (f.get("text") or "")[:80])
        if not found:
            raise SystemExit("FAIL: scheduled post not listed.")

        print("[3/3] cancel scheduled via menu")
        cancel = await page.evaluate(CANCEL_VIA_MENU, tag)
        print(f"      -> {cancel}")
        await page.wait_for_timeout(2000)

        await page.goto(SCHEDULED_URL)
        await page.wait_for_timeout(3000)
        remaining = await page.evaluate(INTROSPECT_SCHEDULED, tag)
        print(f"      remaining: {len(remaining)}")


if __name__ == "__main__":
    asyncio.run(main())
