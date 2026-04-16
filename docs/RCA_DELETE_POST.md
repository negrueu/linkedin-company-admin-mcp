# Root cause analysis: `company_delete_post` flakiness

## Symptoms observed in v1 (TypeScript port)

When running `company_delete_post` against a KETU AI admin-side page:

1. `page.click('button[aria-label*="control menu"]')` would time out with
   `locator.click: Timeout 30000ms exceeded`.
2. The DOM showed the button present, visible, and enabled.
3. Manual clicks in the browser worked fine.
4. 10+ incremental fixes across three days did not resolve it.

## Diagnosis

Inspecting `document.elementsFromPoint(btnRect.x, btnRect.y)` revealed
that the topmost element was not the menu button but a sibling element
with id `artdeco-modal-outlet`. The outlet:

- Is rendered at the top of the `<body>` on every admin navigation.
- Has `position: fixed; inset: 0; pointer-events: auto;` in a number of
  recent CSS revisions (the style leaks from a prior open modal).
- Is transparent and visually invisible.
- Contains no child modal when no dialog is actually shown.

Playwright's actionability checks consider the menu button as "covered"
because the outlet sits above it. The click therefore aborts with a
timeout.

## Why previous strategies failed

| Attempt                                            | Outcome                       |
|----------------------------------------------------|-------------------------------|
| Multi-selector retry                               | Same blocker, 10s wasted      |
| `locator.click({ force: true })` in TS            | Still blocked by actionability |
| `page.evaluate(el.click)` without removing outlet | Dispatched click fired from bubbled listener, but LinkedIn's React event handler is registered at the button; the outlet ate the event. |
| Voyager API DELETE                                 | Endpoint does not exist        |
| Voyager PARTIAL_UPDATE `lifecycleState=ARCHIVED`   | URN format mismatch (activity vs ugcPost vs share) |

## Fix (current implementation)

Remove the stray outlets from the DOM before any interaction. The outlet
is a phantom - no modal is actually open, so deletion is safe:

```py
await page.evaluate(
    "() => document.querySelectorAll("
    "'#artdeco-modal-outlet, [class*=\"modal-outlet\"]'"
    ").forEach((el) => el.remove())"
)
```

Then open the control menu and dispatch Delete clicks through `.click()`
in the page context, skipping Playwright's actionability pipeline:

```py
await page.evaluate(
    "(sel) => { document.querySelector(sel).click(); }",
    target_selector,
)
```

Implementation lives in:

- `linkedin_company_admin_mcp/providers/shared.py`
  (`remove_blocking_modal_outlet`, `js_click_by_text`)
- `linkedin_company_admin_mcp/providers/posts.py` (`delete_post`)

## Validation

Covered by integration smoke path `tests/e2e/test_company_delete_post.py`
(marker `@slow`), which requires a live LinkedIn session and a throwaway
company test post. Run with `LINKEDIN_TEST_ENABLED=1 uv run pytest -m slow`.

If LinkedIn ships a future CSS revision that removes the outlet entirely,
the code still works - the extra `evaluate` call is a no-op on an empty
`querySelectorAll` result.
