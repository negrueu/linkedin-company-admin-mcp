# Guidance for AI agents (Claude, etc.)

## Project purpose

MCP server exposing ~24 tools for LinkedIn Company Page administration, plus a few Personal -> Company bridge tools for employee advocacy workflows.

Complementary to `stickerdaniel/linkedin-mcp-server` (which covers personal LinkedIn). We intentionally do NOT re-implement feed reading, personal messaging, personal search, or connection management.

## Core principles

1. **Browser-first write path** via Patchright (headless Chromium, stealth). No Voyager internal API, no Community Management API (yet).
2. **Zero credentials stored.** Login is always interactive (`--login` opens visible Chromium). Session lives in a persistent profile dir chmod'd to `0o700` on Unix.
3. **Selectors must be aria-label / role / innerText based.** NEVER obfuscated CSS classes like `_8898b74d__foo`. When LinkedIn ships a new UI, the only file that changes is `selectors/__init__.py`.
4. **No god-files.** Max ~300 lines per file. If it gets bigger, split by responsibility.
5. **Tests matter.** Unit tests for selectors + URN parsing + config. Integration tests use captured HTML fixtures (deterministic). E2E is manual-only (marker `@slow`).
6. **Rate limiting is applied, not just imported.** Every write tool is wrapped in `@rate_limited(...)`.
7. **Systematic debugging before fixing.** Never "try strategy N" without root cause analysis.

## File layout

Flat layout (no `src/`). Package is `linkedin_company_admin_mcp/` at the repo root. Tool groups live in `tools/*.py`, each exposing a `register_X_tools(mcp: FastMCP)` factory called from `server.py::create_mcp_server()`.

## Commit rules

- Commit messages in English (only).
- Prefer small, focused commits with imperative subject ("add company_read_page tool").
- Any bug fix commit must include a `Root cause:` line explaining what was actually wrong.

## Running locally

```bash
uv sync
uv run pytest tests/unit        # fast
uv run ruff check .
uv run ruff format --check .
uv run mypy linkedin_company_admin_mcp
```

Integration and e2e tests require `LINKEDIN_TEST_ENABLED=1` and a live session; skip by default.
