# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-04-17

### Added

- `--debug-snapshot` CLI flag and `LINKEDIN_DEBUG_SNAPSHOT` env var: when any tool error occurs, the package writes an `<tool>_<timestamp>.html` + `.png` pair next to the profile directory, so bug reports can be reproduced from evidence.
- `SelectorError` now carries `selector_name`, `last_verified` and `url` keyword-only fields; user-visible messages end with a hint to re-run with `--debug-snapshot`.
- `--check-selectors` CLI subcommand: exits 3 when any entry in the selector registry is older than `--max-age-days` (default 60). CI-friendly, no browser required.
- Startup warning logged by `create_mcp_server()` when stale selectors are present.
- Opt-in persistent rate limiting via `LINKEDIN_RATE_LIMIT_PERSIST=1`. State is stored in `<profile-parent>/rate-limits.db` (sqlite) and survives restarts.
- `selector-canary` GitHub Actions workflow (weekly cron). `staleness-audit` job always runs; optional `live-probe` job is gated behind `SELECTOR_CANARY_ENABLED` repo variable + `LINKEDIN_PROFILE_B64` secret because running Patchright from data-center IPs carries account detection risk.
- Romanian README translation in [docs/README.ro.md](docs/README.ro.md), linked from the English README.
- Synthetic HTML fixtures under `tests/fixtures/synthetic/` (handwritten, no PII, safe to commit) and `test_selectors_resolve.py` assertions proving the registered selectors still map onto the DOM structures we last captured for delete/edit/schedule/reshare/edit-about flows.

### Changed

- `delete_post` now raises an enriched `SelectorError` with `selector_name="OPTION_DELETE_LI"` and `last_verified="2026-04-17"`.

### Security

- No behavioural change vs v0.1.0. Session cookies remain sensitive and must not be synced to cloud storage; this is now called out explicitly in README, README.ro, and TROUBLESHOOTING.

## [0.1.0.post1] - 2026-04-17

### Security

- **History rewrite.** Removed captured HTML fixtures (`tests/integration/fixtures/sample_html/`, 16 files, ~15 MB) from the entire git history using `git filter-repo`. The snapshots had been captured from a live LinkedIn Company Page admin session and contained PII (admin names, follower profiles, analytics). Existing clones should be discarded and re-cloned. The `v0.1.0` tag was re-pointed to the equivalent commit on the rewritten branch; the PyPI `0.1.0` wheel and sdist never contained fixtures and are unaffected.
- `.gitignore` and `.gitattributes` added so future captured HTML cannot be committed by accident and is excluded from GitHub language stats.

## [0.1.0] - 2026-04-17

First public release on PyPI. End-to-end validated 2026-04-17 on a live
LinkedIn Company Page (KETU AI SRL, id 106949933). 13 tools confirmed
✅ and 8 tools ⚠ with explicit preconditions documented in
[docs/TOOL_REFERENCE.md](docs/TOOL_REFERENCE.md).

### Changed (2026-04-17)

- Reworked company admin + content providers for LinkedIn's 2026-04 UI
  after a live end-to-end pass on KETU AI SRL (id 106949933):
  - `company_read_page` now reads the `?editPage=true` modal form fields.
  - `company_edit_post` / `company_delete_post` navigate to the post-detail
    URL `/feed/update/<urn>/` and use `li.option-edit-share` /
    `li.option-delete` - the control menu is no longer exposed on
    `/admin/page-posts/published/`.
  - `company_schedule_post` drives the two-step Schedule post -> date/time
    -> Next -> Schedule flow in the browser's local timezone; respects
    LinkedIn's 15-minute quantised time slots.
  - `company_list_scheduled` reads the share-box management dialog (no
    standalone URL) and gained an optional `cancel_index` parameter.
  - `company_reshare_post` switches the composer actor from the default
    personal identity to the company page before posting.
  - `company_edit_about` / `company_update_details` use the Details tab
    of the Edit Page modal, type via the keyboard so Ember's dirty-state
    flag flips, and surface server-side validation errors so a missing
    required field no longer silently no-ops a save.
  - Bridge tools: personal composer trigger updated for the
    `div[role="button"]` wrapping (not `<button>`); editor selector
    scoped to `div.artdeco-modal` so the always-present video.js hidden
    dialogs do not match.
- Python runtime pinned to 3.12 via `.python-version` so the cp314
  native greenlet binary does not trip Windows Smart App Control.

### Added

- Project bootstrap: `pyproject.toml`, ruff, mypy, pytest, GitHub Actions CI.
- Core infrastructure: `BrowserManager` (persistent Patchright context with 0o700 profile),
  interactive `--login` / `--logout` flow, `SessionInfo`, sliding-window rate limiter,
  URN utilities, configuration loader, CLI entry point.
- Session tools: `session_status`, `session_warmup`, `session_logout`.
- Company read tools: `company_read_page`, `company_list_posts`, `company_list_followers`,
  `company_list_mentions`, `company_manage_admins`, `company_analytics`.
- Admin write tools: `company_edit_about`, `company_edit_logo`, `company_update_details`,
  backed by an `AdminProvider` abstraction.
- Content tools: `company_create_post`, `company_edit_post`, `company_delete_post`,
  `company_schedule_post`, `company_reply_comment`, `company_reshare_post`, backed
  by a `PostsProvider` abstraction. Root-cause analysis for the `artdeco-modal-outlet`
  overlay documented in `docs/RCA_DELETE_POST.md`.
- Growth tools: `company_invite_to_follow` (hard-capped, aware of LinkedIn's
  250/month quota), `company_list_scheduled`.
- Personal -> Company bridge tools: `personal_tag_company`, `personal_reshare_company_post`,
  `personal_comment_as_admin`, `personal_read_company_mentions`.
- Docs: `README.md` with full tool table, `docs/TOOL_REFERENCE.md` (arguments, returns,
  end-to-end examples), `docs/TROUBLESHOOTING.md`, `docs/CONTRIBUTING.md`,
  `docs/RCA_DELETE_POST.md`.
- Packaging: MIT `LICENSE`, `manifest.json` for Claude Desktop MCPB bundle, multi-stage
  `Dockerfile` with non-root `mcp` user and Patchright Chromium, `.dockerignore`.
