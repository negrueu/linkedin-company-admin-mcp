# Contributing

Thanks for your interest in contributing to linkedin-company-admin-mcp.

## Local setup

```bash
git clone https://github.com/negrueu/linkedin-company-admin-mcp.git
cd linkedin-company-admin-mcp
uv sync --all-extras
uv run pre-commit install
```

## Running the test suite

```bash
# Fast unit tests
uv run pytest tests/unit

# Integration tests (requires a logged-in browser profile)
LINKEDIN_TEST_ENABLED=1 uv run pytest tests/integration

# All except slow / e2e
uv run pytest -m "not slow"
```

## Code quality

```bash
uv run ruff check .
uv run ruff format .
uv run mypy linkedin_company_admin_mcp
```

Pre-commit hooks enforce these automatically on every commit.

## Adding a new tool

1. Pick the right module under `linkedin_company_admin_mcp/tools/` (or create one if a new category).
2. Add an `async def` function decorated with `@mcp.tool(...)` and register it inside the module's `register_X_tools(mcp)` factory.
3. Use `ctx: Context` parameter to emit progress for long-running operations.
4. Route all exceptions through `error_handler.raise_tool_error(e, "tool_name")`.
5. Add a unit test (parsing / selector / URN logic) under `tests/unit/`.
6. If the tool hits a real LinkedIn page, capture the HTML snippet as a fixture under `tests/integration/fixtures/sample_html/` and write an integration test that exercises the parser deterministically.
7. Add an entry to `docs/TOOL_REFERENCE.md`.
8. Update `CHANGELOG.md`.

## Selector hygiene

Selectors live in a single file: `linkedin_company_admin_mcp/selectors/__init__.py`.

Rules:

- Prefer `aria-label`, `role`, `id`, and `innerText` matching over CSS classes.
- Never encode hashed class names like `_8898b74d__foo` -- those change weekly.
- Every entry should carry a `# last verified YYYY-MM-DD` comment.

## Commit style

English, imperative mood. Example subject lines:

- `add company_list_followers tool`
- `fix selector drift on admin dashboard`
- `refactor browser singleton lifecycle`

For bug fixes include a `Root cause:` line in the body explaining what actually broke, not just how you patched it.

## Pull requests

- Keep PRs focused. One feature / one fix per PR.
- Update `CHANGELOG.md` under `[Unreleased]`.
- Ensure CI is green (lint + type + tests).

## Selector drift canary (maintainers only)

Weekly GitHub Actions job `selector-canary` has two parts. The first part (`staleness-audit`) always runs and calls `--check-selectors --max-age-days 60`; if any entry is stale, the job exits non-zero and GitHub emails the repo admin.

The second part (`live-probe`) opens a real browser against LinkedIn with a stored session. It is **disabled by default** because running Patchright from a data-center IP carries account detection risk. To enable:

1. Set repo variable `SELECTOR_CANARY_ENABLED=true`.
2. Set repo variable `LINKEDIN_CANARY_COMPANY_ID=<numeric id>` for a page the session is already admin on.
3. Create a dedicated LinkedIn account (do NOT use your main one) and log it in locally with `--login`.
4. Tar + gzip + base64 the profile and store it as secret `LINKEDIN_PROFILE_B64`:
   `tar -czf - -C ~/.linkedin-company-admin profile | base64 -w0`
5. Manually trigger `selector-canary` from the Actions tab.

Accept that the canary account may eventually get restricted. Rotate the secret after every local re-login.
