# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security (2026-04-17)

- **History rewrite.** Removed captured HTML fixtures
  (`tests/integration/fixtures/sample_html/`, 16 files, ~15 MB) from the
  entire git history using `git filter-repo`. The snapshots had been
  captured from a live LinkedIn Company Page admin session and contained
  PII (admin names, follower profiles, analytics). Existing clones should
  be discarded and re-cloned. The `v0.1.0` tag was re-pointed to the
  equivalent commit on the rewritten branch; the PyPI `0.1.0` wheel and
  sdist never contained fixtures and are unaffected.
- `.gitignore` and `.gitattributes` added so future captured HTML cannot
  be committed by accident and is excluded from GitHub language stats.

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
