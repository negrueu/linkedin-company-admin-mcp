"""Shared helpers for Patchright-based providers.

Isolated here so each provider module stays under ~300 lines and so the
helpers can be unit-tested in isolation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from patchright.async_api import Page


async def dirty_state_trigger(page: Page, locator_selector: str) -> None:
    """Fire an ``input`` event on a rich-text editor.

    Quill (LinkedIn's editor) does not enable the Save/Post button until a
    real user-like input event occurs. Calling ``page.fill`` is insufficient:
    we also tap space + backspace so the editor's change listener fires.
    """
    await page.press(locator_selector, "End")
    await page.press(locator_selector, "Space")
    await page.press(locator_selector, "Backspace")


async def quill_insert_text(page: Page, editor_selector: str, text: str) -> None:
    """Insert ``text`` into a Quill-based editor reliably.

    Uses ``document.execCommand`` because it dispatches the Delta events
    Quill listens for - ``page.fill`` bypasses them.
    """
    await page.focus(editor_selector)
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


async def remove_blocking_modal_outlet(page: Page) -> None:
    """Delete LinkedIn's stray modal-outlet overlays.

    **Root cause (documented, v1 incident):**
    On admin-side pages (``/company/<id>/admin/*``), LinkedIn keeps an
    invisible element ``#artdeco-modal-outlet`` mounted in the DOM. It has
    ``pointer-events: auto`` in some CSS revisions and Playwright's
    actionability checks consider it as "covering" the button the caller
    is trying to click. The click therefore times out even though the
    button is fully rendered and enabled.

    **Fix:** remove these outlets before interacting with any admin menu.
    Safe because no modal is actually open at this point - the outlet is
    a phantom from the prior navigation.
    """
    await page.evaluate(
        "() => document.querySelectorAll("
        "'#artdeco-modal-outlet, [class*=\"modal-outlet\"]'"
        ").forEach((el) => el.remove())"
    )


async def js_click_by_text(page: Page, container_selector: str, text_fragment: str) -> bool:
    """Click the first descendant of ``container_selector`` whose ``innerText``
    contains ``text_fragment`` (case-insensitive).

    Bypasses Playwright actionability checks by invoking ``.click()``
    directly in the page context. Returns ``True`` if a click was
    dispatched, ``False`` when nothing matched.
    """
    dispatched: bool = await page.evaluate(
        "([sel, frag]) => {"
        "  const root = document.querySelector(sel);"
        "  if (!root) return false;"
        "  const needle = frag.toLowerCase();"
        "  const candidates = root.querySelectorAll("
        "    '[role=\"menuitem\"], button, li, a'"
        "  );"
        "  for (const node of candidates) {"
        "    const t = (node.innerText || node.textContent || '').trim().toLowerCase();"
        "    if (t.includes(needle)) { node.click(); return true; }"
        "  }"
        "  return false;"
        "}",
        [container_selector, text_fragment],
    )
    return dispatched
