"""E2E: schedule_post then list + cancel via company_list_scheduled."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from linkedin_company_admin_mcp.config.schema import AppConfig, BrowserConfig
from linkedin_company_admin_mcp.core.browser import BrowserManager
from linkedin_company_admin_mcp.providers.base import SchedulePostRequest
from linkedin_company_admin_mcp.providers.posts import BrowserPostsProvider
from linkedin_company_admin_mcp.selectors import COMPANY_ADMIN_SCHEDULED_LIST

KETU = "106949933"


async def main() -> None:
    cfg = AppConfig(browser=BrowserConfig(headless=True))
    target = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=5)
    bump = (15 - target.minute % 15) % 15
    target = target + timedelta(minutes=bump or 15)
    iso = target.strftime("%Y-%m-%dT%H:%M")
    body = f"[e2e-sched2-{target.strftime('%H%M')}] will be cancelled via list_scheduled"

    async with BrowserManager(cfg.browser) as browser:
        posts = BrowserPostsProvider(browser)
        print(f"[1/4] schedule_post at={iso}")
        r = await posts.schedule_post(
            SchedulePostRequest(company_id=KETU, text=body, scheduled_at_iso=iso)
        )
        print(f"      -> {r.ok} {r.detail}")

        page = await browser.get_page()
        await page.goto(
            COMPANY_ADMIN_SCHEDULED_LIST.format(company_id=KETU),
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await page.wait_for_selector('[role="dialog"]', timeout=15_000)
        await page.wait_for_timeout(3000)

        # Inline copy of _JS_LIST_SCHEDULED to avoid importing private constant.
        list_js = r"""async () => {
            for (let i = 0; i < 10; i++) {
                if (document.querySelector('li.share-post-list-view__item')) break;
                await new Promise(r => setTimeout(r, 500));
            }
            const rows = Array.from(document.querySelectorAll('li.share-post-list-view__item'));
            return rows.map((li, idx) => {
                const preview = li.querySelector('button');
                const aria = preview ? (preview.getAttribute('aria-label') || '') : '';
                const m = aria.match(/published on (.+?), click to see/i);
                const when = m ? m[1].trim() : null;
                const lines = (li.innerText || '').split('\n').map(s => s.trim()).filter(Boolean);
                const body = lines.slice(2).join('\n');
                return { index: idx, scheduled_at_display: when, scheduled_by: lines[0], text: body.slice(0, 500) };
            });
        }"""
        print("[2/4] list scheduled")
        rows = await page.evaluate(list_js)
        for row in rows:
            print(
                "      row:", row["index"], "|", row["scheduled_at_display"], "|", row["text"][:60]
            )

        # Find the index where our body marker lives
        target_idx = next((r["index"] for r in rows if body[:20] in (r["text"] or "")), None)
        if target_idx is None:
            raise SystemExit("FAIL: just-scheduled post not listed")
        print(f"[3/4] cancel index={target_idx}")
        cancel_js = r"""async (index) => {
            const rows = Array.from(document.querySelectorAll('li.share-post-list-view__item'));
            if (index >= rows.length) return { phase: 'index-oob' };
            const trigger = rows[index].querySelector('button.share-post-action-bar__dropdown-trigger');
            trigger.click();
            await new Promise(r => setTimeout(r, 1200));
            const dd = Array.from(document.querySelectorAll('.artdeco-dropdown__content--is-open')).find(el => el.offsetParent !== null);
            if (!dd) return { phase: 'dropdown' };
            const del = Array.from(dd.querySelectorAll('button, [role="button"], a, .artdeco-dropdown__item')).find(el => (el.innerText || '').trim().toLowerCase() === 'delete post');
            if (!del) return { phase: 'delete-item' };
            del.click();
            await new Promise(r => setTimeout(r, 2500));
            const confirm = Array.from(document.querySelectorAll('[role="alertdialog"] button, [role="dialog"] button')).find(b => /^delete$/i.test((b.textContent || '').trim()) && !b.disabled && b.offsetParent !== null);
            if (!confirm) return { phase: 'confirm' };
            confirm.click();
            await new Promise(r => setTimeout(r, 2000));
            return { ok: true };
        }"""
        result = await page.evaluate(cancel_js, target_idx)
        print(f"      -> {result}")

        print("[4/4] verify gone")
        await page.wait_for_timeout(2500)
        rows_after = await page.evaluate(list_js)
        present = any(body[:20] in (r["text"] or "") for r in rows_after)
        print(f"      rows_after={len(rows_after)} still_present={present}")


if __name__ == "__main__":
    asyncio.run(main())
